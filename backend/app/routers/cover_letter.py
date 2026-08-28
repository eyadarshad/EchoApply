import logging
import json
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.schemas import CoverLetterRequest, CoverLetterResponse, ResumeParsedData
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.services.cover_letter import generate_cover_letter, format_cover_letter_html
from app.database import get_db
from app.utils import clean_uuid
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cover_letter"])

@router.post("/api/cover-letter/generate", response_model=CoverLetterResponse)
@limiter.limit("10/minute")
async def api_generate_cover_letter(request: Request, payload: CoverLetterRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Generate a tailored cover letter from resume data and job description.
    Rate limited to 10/minute to control LLM costs.
    """
    if user and user.user_id:
        payload.user_id = user.user_id
    else:
        sanitized_id = sanitize_user_id(payload.user_id) if payload.user_id else None
        if not sanitized_id and not payload.parsed_resume:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
        payload.user_id = sanitized_id or "guest"
    if payload.jd_text:
        payload.jd_text = sanitize_text_input(payload.jd_text, field_name="jd_text")
    if payload.company_name:
        payload.company_name = sanitize_text_input(payload.company_name, max_length=150, field_name="company_name")
    if payload.role_title:
        payload.role_title = sanitize_text_input(payload.role_title, max_length=150, field_name="role_title")

    logger.info(f"[CoverLetter] Request from user {payload.user_id}")
    
    if not payload.jd_text or len(payload.jd_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description must be at least 50 characters long."
        )
    
    # Get parsed resume from payload or try to load from DB
    parsed_resume = payload.parsed_resume
    if not parsed_resume:
        # Try loading from database
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT parsed_resume_json FROM profiles WHERE user_id = %s;",
                            (clean_uuid(payload.user_id),)
                        )
                        row = await cur.fetchone()
                        if row and row[0]:
                            parsed_resume = ResumeParsedData.model_validate(row[0])
        except Exception as e:
            logger.warning(f"Could not load resume from DB: {e}")
    
    if not parsed_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume data available. Please upload a resume first or include parsed_resume in the request."
        )
    
    result = await generate_cover_letter(
        parsed_resume=parsed_resume,
        jd_text=payload.jd_text,
        company_name=payload.company_name,
        role_title=payload.role_title,
    )
    
    return CoverLetterResponse(**result)


@router.post("/api/cover-letter/download-pdf")
@limiter.limit("10/minute")
async def download_cover_letter_pdf(request: Request, payload: CoverLetterRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Generate a cover letter and return it as a downloadable PDF.
    """
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access/modify this resource"
        )
    payload.user_id = sanitized_id
    if payload.jd_text:
        payload.jd_text = sanitize_text_input(payload.jd_text, field_name="jd_text")
    if payload.company_name:
        payload.company_name = sanitize_text_input(payload.company_name, max_length=150, field_name="company_name")
    if payload.role_title:
        payload.role_title = sanitize_text_input(payload.role_title, max_length=150, field_name="role_title")
    # First generate the text
    parsed_resume = payload.parsed_resume
    if not parsed_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parsed_resume is required for PDF generation."
        )
    
    result = await generate_cover_letter(
        parsed_resume=parsed_resume,
        jd_text=payload.jd_text,
        company_name=payload.company_name,
        role_title=payload.role_title,
    )
    
    if result["status"] != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cover letter generation failed: {result.get('error', 'Unknown error')}"
        )
    
    # Convert to PDF via WeasyPrint (with fallback)
    html_content = format_cover_letter_html(
        text=result["cover_letter_text"],
        candidate_name=parsed_resume.name,
        candidate_email=parsed_resume.email,
    )
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.warning(f"WeasyPrint failed for cover letter, using text fallback: {e}")
        # Fallback: return as plain text
        return Response(
            content=result["cover_letter_text"].encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=cover_letter.txt"}
        )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cover_letter.pdf"}
    )
