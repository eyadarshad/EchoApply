import logging
from typing import Dict, List, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.sanitize import sanitize_user_id
from app.utils import clean_uuid
from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

class AnalyticsSummaryResponse(BaseModel):
    total_applied: int
    conversion_funnel: Dict[str, int]
    avg_ats_score: float
    applications_timeline: List[Dict[str, Any]]

@router.get("/api/analytics/summary", response_model=AnalyticsSummaryResponse)
@limiter.limit("20/minute")
async def get_analytics_summary(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve application statistics and ATS score averages to power dashboard charts."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access analytics for this user"
        )
    user_id = sanitized_id
    user_uuid = clean_uuid(user_id)
    
    total = 0
    funnel = {"pending": 0, "applied": 0, "interviewing": 0, "offered": 0}
    avg_ats = 0.0
    timeline = []
    
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM applications WHERE user_id = %s;", (user_uuid,))
                    row = await cur.fetchone()
                    if row:
                        total = row[0]
                    
                    await cur.execute("SELECT status, COUNT(*) FROM applications WHERE user_id = %s GROUP BY status;", (user_uuid,))
                    rows = await cur.fetchall()
                    for status_name, count in rows:
                        if status_name in funnel:
                            funnel[status_name] = count
                    
                    await cur.execute("SELECT COALESCE(AVG(ats_score), 0.0) FROM tailored_resumes WHERE user_id = %s;", (user_uuid,))
                    avg_row = await cur.fetchone()
                    if avg_row:
                        avg_ats = float(avg_row[0])
                    
                    await cur.execute(
                        """
                        SELECT applied_at::date, COUNT(*) 
                        FROM applications 
                        WHERE user_id = %s 
                        GROUP BY applied_at::date 
                        ORDER BY applied_at::date ASC;
                        """,
                        (user_uuid,)
                    )
                    timeline_rows = await cur.fetchall()
                    for date, count in timeline_rows:
                        timeline.append({"date": date.isoformat(), "count": count})
    except Exception as e:
        logger.error(f"Failed to query analytics summary: {e}")
        pass
        
    return AnalyticsSummaryResponse(
        total_applied=total,
        conversion_funnel=funnel,
        avg_ats_score=avg_ats,
        applications_timeline=timeline
    )

class OutcomeInsight(BaseModel):
    category: str
    title: str
    text: str

@router.get("/api/analytics/insights", response_model=List[OutcomeInsight])
@limiter.limit("20/minute")
async def get_analytics_insights(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve outcome feedback loop insights based on historical metrics."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id or clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        
    from app.services.outcome_engine import get_outcome_insights
    return get_outcome_insights(sanitized_id)
