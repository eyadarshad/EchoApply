import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, get_optional_user, AuthenticatedUser
from app.schemas import JobSearchRequest, JobSearchResponse
from app.sanitize import sanitize_search_query, sanitize_user_id
from app.services.job_service import JobService
from app.database import get_db
from app.utils import clean_uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])

job_service = JobService()

class SavedSearchCreateRequest(BaseModel):
    user_id: str
    keywords: str
    location: Optional[str] = None
    alert_interval: str = "weekly"

class SavedSearchResponse(BaseModel):
    id: str
    user_id: str
    keywords: str
    location: Optional[str] = None
    alert_interval: str
    created_at: str

@router.post("/jobs/search", response_model=JobSearchResponse)
@limiter.limit("20/minute")
async def search_jobs(request: Request, payload: JobSearchRequest, user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
    """
    Search and rank job listings from multiple aggregators.
    """
    if payload.user_id:
        sanitized_id = sanitize_user_id(payload.user_id)
        if sanitized_id:
            if user and clean_uuid(user.user_id) != clean_uuid(sanitized_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to query search history/alerts for this user"
                )
            payload.user_id = sanitized_id
        else:
            payload.user_id = None
    if payload.query:
        payload.query = sanitize_search_query(payload.query)
    if payload.location:
        payload.location = sanitize_search_query(payload.location)
    try:
        return await job_service.search_and_rank_jobs(payload)
    except Exception as e:
        logger.error(f"Error in /jobs/search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during job search: {str(e)}"
        )

@router.post("/api/jobs/alerts", response_model=SavedSearchResponse)
@limiter.limit("10/minute")
async def create_job_alert(request: Request, payload: SavedSearchCreateRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Save keywords and location query as an automated job alert."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to manage alerts for this user"
        )
    payload.user_id = sanitized_id
    if payload.keywords:
        payload.keywords = sanitize_search_query(payload.keywords)
    if payload.location:
        payload.location = sanitize_search_query(payload.location)

    alert_id = str(uuid.uuid4())
    user_uuid = clean_uuid(payload.user_id)
    
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    # Ensure user exists in users table (FK constraint fix)
                    # User may exist in Supabase Auth but not in our app's users table
                    # if they signed up but haven't uploaded a resume yet
                    await cur.execute(
                        """
                        INSERT INTO users (id, email, created_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        (user_uuid, user.email or "unknown@user")
                    )
                    await cur.execute(
                        """
                        INSERT INTO saved_searches (id, user_id, keywords, location, alert_interval, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        RETURNING created_at;
                        """,
                        (alert_id, user_uuid, payload.keywords, payload.location, payload.alert_interval)
                    )
                    created_at = (await cur.fetchone())[0]
                    await conn.commit()
                    
                    return SavedSearchResponse(
                        id=alert_id,
                        user_id=payload.user_id,
                        keywords=payload.keywords,
                        location=payload.location,
                        alert_interval=payload.alert_interval,
                        created_at=created_at.isoformat()
                    )
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save job alert: {e}")
        err_msg = str(e)
        if "saved_searches" in err_msg and ("does not exist" in err_msg or "UndefinedTable" in err_msg):
            raise HTTPException(status_code=500, detail="Job alerts table has not been initialized. Please run database migrations.")
        raise HTTPException(status_code=500, detail=f"Failed to save alert. Please try again.")

@router.get("/api/jobs/alerts", response_model=List[SavedSearchResponse])
@limiter.limit("20/minute")
async def get_job_alerts(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve all active saved search alerts for a specific user ID."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access these alerts"
        )
    user_id = sanitized_id
    user_uuid = clean_uuid(user_id)
    alerts = []
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, keywords, location, alert_interval, created_at 
                        FROM saved_searches 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC;
                        """,
                        (user_uuid,)
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        alerts.append(
                            SavedSearchResponse(
                                id=str(row[0]),
                                user_id=user_id,
                                keywords=row[1],
                                location=row[2],
                                alert_interval=row[3],
                                created_at=row[4].isoformat()
                            )
                        )
    except Exception as e:
        err_msg = str(e)
        if "saved_searches" in err_msg and ("does not exist" in err_msg or "UndefinedTable" in err_msg):
            logger.warning(f"saved_searches table not found, returning empty alerts: {e}")
            return []
        logger.error(f"Failed to query job alerts: {e}")
        # Return empty instead of 500 for better UX
        return []
        
    return alerts

@router.delete("/api/jobs/alerts/{alert_id}")
@limiter.limit("20/minute")
async def delete_job_alert(request: Request, alert_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Deletes/unsubscribes a specific saved search alert."""
    alert_uuid = clean_uuid(alert_id)
    user_uuid = clean_uuid(user.user_id)
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT user_id FROM saved_searches WHERE id = %s;", (alert_uuid,))
                    row = await cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail="Alert not found")
                    owner_uuid = clean_uuid(str(row[0]))
                    if owner_uuid != user_uuid:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Forbidden: You do not have permission to delete this alert"
                        )
                    
                    await cur.execute("DELETE FROM saved_searches WHERE id = %s;", (alert_uuid,))
                    await conn.commit()
                    return {"status": "success", "message": "Alert deleted successfully"}
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/jobs/alerts/run-check")
async def trigger_job_alerts_check():
    """Trigger the automated job alerts scanner and notification email worker."""
    from app.tasks import run_job_alerts_check
    result = await run_job_alerts_check()
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result
