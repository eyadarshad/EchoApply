import logging
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_optional_user, AuthenticatedUser
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.utils import clean_uuid
from app.database import get_db
from app.services.interview_service import (
    generate_mock_questions,
    grade_mock_answer
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interview"])

async def _fetch_user_profile_data(user_uuid: str) -> dict:
    """Fetch parsed resume json for a given user UUID."""
    profile_data = {}
    if not user_uuid or user_uuid.startswith("00000000"):
        return profile_data
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (user_uuid,))
                    row = await cur.fetchone()
                    if row and row[0]:
                        profile_data = row[0]
    except Exception as e:
        logger.warning(f"Could not load user profile from database: {e}")
    return profile_data

class InterviewQuestionsRequest(BaseModel):
    user_id: Optional[str] = "00000000-0000-0000-0000-000000000001"
    job_title: str = "Software Engineer"
    jd_text: str

class InterviewQuestionsResponse(BaseModel):
    questions: List[str]

class InterviewGradeRequest(BaseModel):
    question: str
    answer: str

class InterviewGradeResponse(BaseModel):
    score: int
    star_compliance: str
    tech_depth: str
    communication_clarity: str
    constructive_tips: List[str]

@router.post("/api/interview/questions", response_model=InterviewQuestionsResponse)
@limiter.limit("15/minute")
async def get_interview_questions(
    request: Request,
    payload: InterviewQuestionsRequest,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """Retrieve custom technical/behavioral interview questions based on profile and JD."""
    effective_id = user.user_id if user and user.user_id else (payload.user_id or "00000000-0000-0000-0000-000000000001")
    sanitized_id = sanitize_user_id(effective_id) or "00000000-0000-0000-0000-000000000001"
    
    if payload.job_title:
        payload.job_title = sanitize_text_input(payload.job_title, max_length=150, field_name="job_title")
    if payload.jd_text:
        payload.jd_text = sanitize_text_input(payload.jd_text, field_name="jd_text")

    user_uuid = clean_uuid(sanitized_id)
    profile_data = await _fetch_user_profile_data(user_uuid)
    
    questions = await asyncio.to_thread(
        generate_mock_questions,
        profile_data,
        payload.job_title or "Software Engineer",
        payload.jd_text or ""
    )
    return InterviewQuestionsResponse(questions=questions)

@router.post("/api/interview/grade", response_model=InterviewGradeResponse)
@limiter.limit("20/minute")
async def grade_interview_response(
    request: Request,
    payload: InterviewGradeRequest,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """Evaluate candidate mock response against structural clarity and technical metrics."""
    q = sanitize_text_input(payload.question, field_name="question") if payload.question else ""
    a = sanitize_text_input(payload.answer, field_name="answer") if payload.answer else ""
    
    result = await asyncio.to_thread(grade_mock_answer, q, a)
    return InterviewGradeResponse(
        score=result.get("score", 70),
        star_compliance=result.get("star_compliance", ""),
        tech_depth=result.get("tech_depth", ""),
        communication_clarity=result.get("communication_clarity", ""),
        constructive_tips=result.get("constructive_tips", [])
    )

class STARHintTemplate(BaseModel):
    situation: str
    task: str
    action: str
    result: str

class AdvancedQuestion(BaseModel):
    question: str
    context: str
    star_template: STARHintTemplate

class AdvancedInterviewPrepResponse(BaseModel):
    company_questions: List[AdvancedQuestion]
    resume_questions: List[AdvancedQuestion]

@router.post("/api/interview/prep", response_model=AdvancedInterviewPrepResponse)
@limiter.limit("10/minute")
async def get_advanced_interview_prep(
    request: Request,
    payload: InterviewQuestionsRequest,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """Retrieve advanced company-specific & resume-specific questions with STAR hints."""
    effective_id = user.user_id if user and user.user_id else (payload.user_id or "00000000-0000-0000-0000-000000000001")
    sanitized_id = sanitize_user_id(effective_id) or "00000000-0000-0000-0000-000000000001"
        
    if payload.job_title:
        payload.job_title = sanitize_text_input(payload.job_title, max_length=150, field_name="job_title")
    if payload.jd_text:
        payload.jd_text = sanitize_text_input(payload.jd_text, field_name="jd_text")

    user_uuid = clean_uuid(sanitized_id)
    profile_data = await _fetch_user_profile_data(user_uuid)
    from app.services.interview_service import generate_advanced_interview_prep as gen_prep
    res = await asyncio.to_thread(gen_prep, profile_data, payload.job_title, payload.jd_text)
    return res
