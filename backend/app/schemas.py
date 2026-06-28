from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# ==========================================
# Phase 0: Health and Echo Schema
# ==========================================

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "ok"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EchoRequest(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "Hello from frontend"})

class EchoResponse(BaseModel):
    message: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==========================================
# Phase 1 & 2: Resume Intake & Tailoring
# ==========================================

class ResumeParsedData(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    links: List[str] = []
    education: List[Dict[str, Any]] = []
    experience: List[Dict[str, Any]] = []
    skills: List[str] = []
    projects: List[Dict[str, Any]] = []

class ResumeIntakeResponse(BaseModel):
    user_id: str
    parsed_resume: ResumeParsedData
    github_enriched: Optional[Dict[str, Any]] = None

class ResumeTailorRequest(BaseModel):
    user_id: str
    job_id: str
    additional_context: Optional[str] = None

class ResumeTailorResponse(BaseModel):
    resume_id: str
    user_id: str
    job_id: str
    content_json: Dict[str, Any]
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    ats_score: Optional[int] = None


# ==========================================
# Phase 3 & 5: Job Search & Matching
# ==========================================

class JobCard(BaseModel):
    job_id: str
    source: str
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    apply_url: Optional[str] = None
    jd_text: str
    fetched_at: datetime
    job_hash: str
    match_score: Optional[float] = None
    match_explanation: Optional[str] = None
    is_applied: bool = False

class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    remote_only: bool = False
    limit: int = 50

class JobSearchResponse(BaseModel):
    query_hash: str
    jobs: List[JobCard]


# ==========================================
# Phase 4 & 6: Application & Auto-Apply
# ==========================================

class ScreenQuestionDraft(BaseModel):
    question_id: str
    question_text: str
    drafted_answer: str
    confidence: float = Field(..., description="Value between 0.0 and 1.0 indicating AI confidence")
    needs_user_input: bool = Field(False, description="True if confidence is low and requires clarification")
    warning_message: Optional[str] = None

class DraftAnswersRequest(BaseModel):
    user_id: str
    job_id: str

class DraftAnswersResponse(BaseModel):
    job_id: str
    questions: List[ScreenQuestionDraft]

class ApplicationSubmitRequest(BaseModel):
    user_id: str
    job_id: str
    answers: Dict[str, str] = Field(default_factory=dict)
    opt_in_agent: bool = Field(False, description="True if using Tier-2 agentic auto-apply")

class ApplicationSubmitResponse(BaseModel):
    application_id: str
    status: str = Field(..., description="pending, success, or needs_action")
    action_required: Optional[Dict[str, Any]] = Field(None, description="CAPTCHA or login details required from the user")
