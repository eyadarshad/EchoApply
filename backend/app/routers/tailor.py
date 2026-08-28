import uuid
import logging
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_optional_user, AuthenticatedUser
from app.schemas import ResumeTailorRequest, ResumeTailorResponse, ResumeParsedData
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.database import get_db
from app.utils import clean_uuid
from app.config import settings
from app.services.billing_service import check_entitlement, record_usage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tailoring"])

@router.post("/tailor", response_model=ResumeTailorResponse)
async def tailor_resume(payload: ResumeTailorRequest, user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
    """
    Orchestrates the resume tailoring process for a specific job.
    """
    if user and user.user_id:
        # For authenticated requests, authoritative user ID is the authenticated token
        payload.user_id = user.user_id
    else:
        sanitized_id = sanitize_user_id(payload.user_id) if payload.user_id else None
        if not sanitized_id and not payload.parsed_resume:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
        payload.user_id = sanitized_id or "guest"
    
    if payload.jd_text:
        payload.jd_text = sanitize_text_input(payload.jd_text, field_name="jd_text")
    if payload.additional_context:
        payload.additional_context = sanitize_text_input(payload.additional_context, field_name="additional_context")

    # 1. Resolve the profile data
    profile = payload.parsed_resume
    major = "Computer Science"  # Default major
    
    # If not supplied in payload, attempt to look up from database
    if not profile:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to fetch profile from database."
            )
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT parsed_resume_json, major FROM profiles JOIN users ON users.id = profiles.user_id WHERE user_id = %s;",
                            (payload.user_id,)
                        )
                        row = await cur.fetchone()
                        if row:
                            profile = ResumeParsedData.model_validate(row[0])
                            major = row[1] or "Computer Science"
        except Exception as e:
            logger.warning(f"Could not retrieve profile for tailoring: {e}")

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume profile data is missing."
        )

    # 2. Check billing entitlement
    if not check_entitlement(payload.user_id, "tailor"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Billing limit reached: Upgrade to Pro for unlimited resume tailoring."
        )

    # 2. Resolve job description text
    jd_text = payload.jd_text
    if not jd_text:
        # Attempt to look up from database jobs table
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT jd_text FROM jobs WHERE id = %s;", (payload.job_id,))
                        row = await cur.fetchone()
                        if row:
                            jd_text = row[0]
        except Exception as e:
            logger.warning(f"Could not retrieve job description from database: {e}")
                
    # Raise error if no job description text was supplied and could not be fetched from DB
    if not jd_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text was not supplied and could not be retrieved from the database."
        )

    try:
        # Run tailoring pipeline
        from app.main import tailor_resume_flow
        result = await tailor_resume_flow(profile, jd_text, major)

        # Record usage with configured flash model
        record_usage(payload.user_id, "tailor", tokens_used=5000, cost_usd=0.0005, model=settings.GEMINI_FLASH_MODEL)

        # 3. Store result in database if reachable
        resume_id = str(uuid.uuid4())
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO tailored_resumes (id, user_id, job_id, content_json, ats_score)
                            VALUES (%s, %s, %s, %s, %s);
                            """,
                            (resume_id, payload.user_id, payload.job_id, json.dumps(result["content_json"]), result["ats_score"])
                        )
                        await conn.commit()
        except Exception as db_err:
            logger.warning(f"Database save of tailored resume failed: {db_err}")

        return ResumeTailorResponse(
            resume_id=resume_id,
            user_id=payload.user_id,
            job_id=payload.job_id,
            content_json=result["content_json"],
            ats_score=result["ats_score"],
            gap_analysis=result["gap_analysis"],
            truthfulness_report=result["truthfulness_report"]
        )
    except Exception as e:
        logger.error(f"Tailoring route failure: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during resume tailoring: {str(e)}"
        )
