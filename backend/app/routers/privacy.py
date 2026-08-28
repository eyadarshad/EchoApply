import os
import json
import logging
import datetime
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.database import get_db
from app.config import settings
from app.utils import clean_uuid
from app.sanitize import sanitize_user_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["privacy"])

class ConsentRequest(BaseModel):
    consent_type: str  # 'data_processing', 'ai_processing', 'credential_storage', 'analytics'
    granted: bool

class ConsentStatusResponse(BaseModel):
    consent_type: str
    granted: bool
    granted_at: Optional[datetime.datetime] = None
    revoked_at: Optional[datetime.datetime] = None

@router.post("/api/privacy/consent")
@limiter.limit("10/minute")
async def record_user_consent(
    request: Request,
    payload: ConsentRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Record or update user consent for data processing, AI usage, analytics, or credential storage."""
    allowed_types = {'data_processing', 'ai_processing', 'credential_storage', 'analytics'}
    if payload.consent_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type. Allowed: {allowed_types}"
        )

    user_uuid = clean_uuid(user.user_id)
    ip_address = request.client.host if request.client else None
    now = datetime.datetime.now(datetime.timezone.utc)

    async with get_db() as conn:
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
        
        async with conn.cursor() as cur:
            # Upsert into user_consents
            if payload.granted:
                await cur.execute(
                    """
                    INSERT INTO user_consents (user_id, consent_type, granted, granted_at, ip_address)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, consent_type) DO UPDATE
                    SET granted = TRUE,
                        granted_at = EXCLUDED.granted_at,
                        revoked_at = NULL,
                        ip_address = EXCLUDED.ip_address;
                    """,
                    (user_uuid, payload.consent_type, True, now, ip_address)
                )
            else:
                await cur.execute(
                    """
                    INSERT INTO user_consents (user_id, consent_type, granted, revoked_at, ip_address)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, consent_type) DO UPDATE
                    SET granted = FALSE,
                        revoked_at = EXCLUDED.revoked_at,
                        ip_address = EXCLUDED.ip_address;
                    """,
                    (user_uuid, payload.consent_type, False, now, ip_address)
                )
            await conn.commit()
            
    logger.info(f"Privacy: Recorded consent '{payload.consent_type}'={payload.granted} for user {user.user_id}")
    return {"status": "success", "consent_type": payload.consent_type, "granted": payload.granted}

@router.get("/api/privacy/consent", response_model=List[ConsentStatusResponse])
async def get_user_consent_status(user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve current consent statuses for the authenticated user."""
    user_uuid = clean_uuid(user.user_id)
    
    async with get_db() as conn:
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
        
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT consent_type, granted, granted_at, revoked_at
                FROM user_consents
                WHERE user_id = %s;
                """,
                (user_uuid,)
            )
            rows = await cur.fetchall()
            
    results = []
    for row in rows:
        results.append(
            ConsentStatusResponse(
                consent_type=row[0],
                granted=row[1],
                granted_at=row[2],
                revoked_at=row[3]
            )
        )
    return results

@router.post("/api/privacy/export")
@limiter.limit("2/hour")
async def export_user_data(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """GDPR Article 20: Compiles all stored data for the user into a downloadable JSON structure."""
    user_uuid = clean_uuid(user.user_id)
    logger.info(f"GDPR: Processing data export request for user: {user.user_id}")

    export_payload = {
        "export_metadata": {
            "user_id": user.user_id,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "format_version": "1.0"
        },
        "user_record": {},
        "profile": {},
        "applications": [],
        "tailored_resumes": [],
        "saved_searches": [],
        "consents": []
    }

    async with get_db() as conn:
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
        
        async with conn.cursor() as cur:
            # 1. User details
            await cur.execute("SELECT email, major, location, created_at FROM users WHERE id = %s;", (user_uuid,))
            u_row = await cur.fetchone()
            if u_row:
                export_payload["user_record"] = {
                    "email": u_row[0],
                    "major": u_row[1],
                    "location": u_row[2],
                    "created_at": u_row[3].isoformat() if u_row[3] else None
                }

            # 2. Profile
            await cur.execute("SELECT parsed_resume_json, github_json, linkedin_json, portfolio_json, updated_at FROM profiles WHERE user_id = %s;", (user_uuid,))
            p_row = await cur.fetchone()
            if p_row:
                export_payload["profile"] = {
                    "parsed_resume": p_row[0],
                    "github": p_row[1],
                    "linkedin": p_row[2],
                    "portfolio": p_row[3],
                    "updated_at": p_row[4].isoformat() if p_row[4] else None
                }

            # 3. Applications
            await cur.execute("SELECT id, job_id, job_hash, status, applied_at FROM applications WHERE user_id = %s;", (user_uuid,))
            app_rows = await cur.fetchall()
            for r in app_rows:
                export_payload["applications"].append({
                    "application_id": str(r[0]),
                    "job_id": str(r[1]),
                    "job_hash": r[2],
                    "status": r[3],
                    "applied_at": r[4].isoformat() if r[4] else None
                })

            # 4. Tailored Resumes
            await cur.execute("SELECT id, job_id, content_json, pdf_path, docx_path, ats_score, created_at FROM tailored_resumes WHERE user_id = %s;", (user_uuid,))
            tr_rows = await cur.fetchall()
            for r in tr_rows:
                export_payload["tailored_resumes"].append({
                    "resume_id": str(r[0]),
                    "job_id": str(r[1]),
                    "content_json": r[2],
                    "pdf_path": r[3],
                    "docx_path": r[4],
                    "ats_score": r[5],
                    "created_at": r[6].isoformat() if r[6] else None
                })

            # 5. Saved Searches
            await cur.execute("SELECT id, keywords, location, alert_interval, created_at FROM saved_searches WHERE user_id = %s;", (user_uuid,))
            ss_rows = await cur.fetchall()
            for r in ss_rows:
                export_payload["saved_searches"].append({
                    "search_id": str(r[0]),
                    "keywords": r[1],
                    "location": r[2],
                    "alert_interval": r[3],
                    "created_at": r[4].isoformat() if r[4] else None
                })

            # 6. Consents
            await cur.execute("SELECT consent_type, granted, granted_at, revoked_at, ip_address FROM user_consents WHERE user_id = %s;", (user_uuid,))
            c_rows = await cur.fetchall()
            for r in c_rows:
                export_payload["consents"].append({
                    "consent_type": r[0],
                    "granted": r[1],
                    "granted_at": r[2].isoformat() if r[2] else None,
                    "revoked_at": r[3].isoformat() if r[3] else None,
                    "ip_address": r[4]
                })

    headers = {
        "Content-Disposition": f"attachment; filename=echoapply_user_export_{user.user_id[:8]}.json"
    }
    return JSONResponse(content=export_payload, headers=headers)

@router.delete("/api/privacy/delete-account")
@limiter.limit("1/minute")
async def delete_user_account(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """GDPR Compliance: Completely wipes the user record, credentials, resumes, and cascades down the DB."""
    user_uuid = clean_uuid(user.user_id)
    logger.info(f"GDPR: Initiating self-requested complete account deletion for user: {user.user_id}")
    
    # 1. Clean local credential & resume files
    try:
        fallback_dir = os.path.join(settings.DATA_DIR, "credentials")
        if os.path.exists(fallback_dir):
            for f in os.listdir(fallback_dir):
                if f.startswith(user_uuid):
                    os.remove(os.path.join(fallback_dir, f))
                    
        resumes_dir = os.path.join(settings.DATA_DIR, "resumes")
        if os.path.exists(resumes_dir):
            for f in os.listdir(resumes_dir):
                if f.startswith(user_uuid):
                    os.remove(os.path.join(resumes_dir, f))
    except Exception as cleanup_err:
        logger.warning(f"Failed to clean local storage files: {cleanup_err}")

    # 2. Delete user row in DB (cascades to all user data)
    try:
        async with get_db() as conn:
            if not conn:
                raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
            
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE id = %s;", (user_uuid,))
                await conn.commit()
                
        return {"status": "success", "message": "Your account and all associated data have been permanently deleted."}
    except Exception as e:
        logger.error(f"Failed to execute database delete: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account from database.")
