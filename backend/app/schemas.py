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

class EducationEntry(BaseModel):
    school: str = Field(..., description="Name of the school or university")
    degree: str = Field(..., description="Degree or qualification (e.g. B.S. or High School)")
    date: str = Field(..., description="Graduation year or date range")
    major: Optional[str] = Field(None, description="Field of study or major")
    gpa: Optional[str] = Field(None, description="GPA or grade score")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class ExperienceEntry(BaseModel):
    role: str = Field(..., description="Job role or title")
    company: str = Field(..., description="Company name")
    start_date: str = Field(..., description="Start date (e.g. 2023-01 or Jan 2023)")
    end_date: str = Field(..., description="End date or 'Present'")
    location: Optional[str] = Field(None, description="Job location or 'Remote'")
    bullets: List[str] = Field(default_factory=list, description="Work experience achievement bullet points")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class ProjectEntry(BaseModel):
    name: str = Field(..., description="Name of the project")
    link: Optional[str] = Field(None, description="URL or repository link")
    bullets: List[str] = Field(default_factory=list, description="Project bullet points detailing achievements")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class HighlightSkill(BaseModel):
    skill: str = Field(..., description="The name of the skill")
    relevance_reason: str = Field(..., description="Relevance reasoning for matching the job description")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class PartialSkillMatch(BaseModel):
    jd_skill: str = Field(..., description="Required skill from job description")
    user_skill: str = Field(..., description="Related skill candidate has")
    reason: str = Field(..., description="Explanation of relation / partial match")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class ResumeParsedData(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    links: List[str] = []
    education: List[EducationEntry] = []
    experience: List[ExperienceEntry] = []
    skills: List[str] = []
    projects: List[ProjectEntry] = []
    anchor_line: Optional[str] = None
    highlights_strip: List[HighlightSkill] = []

class ResumeIntakeResponse(BaseModel):
    user_id: str
    parsed_resume: ResumeParsedData
    github_enriched: Optional[Dict[str, Any]] = None

class ResumeTailorRequest(BaseModel):
    user_id: str
    job_id: str
    jd_text: Optional[str] = None
    additional_context: Optional[str] = None
    parsed_resume: Optional[ResumeParsedData] = None

class JDAnalysisResult(BaseModel):
    role_title: str = Field(..., description="Extract the target role title from the JD")
    seniority: str = Field(..., description="Seniority level (e.g. Intern, Entry, Mid, Senior, Lead)")
    required_skills: List[str] = Field(default_factory=list, description="Mandatory technical and soft skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or optional skills")
    key_responsibilities: List[str] = Field(default_factory=list, description="Main job responsibilities")

class GapAnalysisResult(BaseModel):
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in resume that match the JD")
    missing_skills: List[str] = Field(default_factory=list, description="Required/preferred skills in the JD lacking in the resume")
    partial_matches: List[PartialSkillMatch] = Field(default_factory=list, description="List of related skills")

class RewrittenBullet(BaseModel):
    original_bullet: str
    rewritten_bullet: str

class TargetedRewriteResult(BaseModel):
    rewritten_bullets: List[RewrittenBullet] = Field(default_factory=list)

class ImpactPassResult(BaseModel):
    anchor_line: str = Field(..., description="One tailored tagline/title statement under the name")
    highlights_strip: List[HighlightSkill] = Field(default_factory=list, description="Curated list of top 4-5 relevant skills with explanations")
    tailored_experience: List[ExperienceEntry] = Field(default_factory=list, description="Experience section with tailored, prioritized, and page-trimmed bullets")

class BulletVerification(BaseModel):
    rewritten_bullet: str
    is_fabricated: bool = Field(..., description="True if this bullet contains skills, responsibilities, or metrics NOT in or implied by the original resume")
    justification: str = Field(..., description="Detailed explanation of the fabrication if flagged")
    suggested_fix: str = Field(..., description="A fact-only alternative rewriting")

class TruthfulnessCheckResult(BaseModel):
    is_fabricated: bool = Field(..., description="True if any bullet has fabrication flags")
    verification_report: List[BulletVerification] = Field(default_factory=list)

class ResumeTailorResponse(BaseModel):
    resume_id: str
    user_id: str
    job_id: str
    content_json: Dict[str, Any]
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    ats_score: Optional[int] = None
    gap_analysis: Optional[GapAnalysisResult] = None
    truthfulness_report: Optional[TruthfulnessCheckResult] = None


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
    user_id: Optional[str] = None

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
