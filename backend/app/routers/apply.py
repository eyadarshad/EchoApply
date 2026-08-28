import uuid
import logging
import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field
from app.limiter import limiter
from app.auth import get_current_user, get_optional_user, AuthenticatedUser, SUPABASE_JWT_SECRET, _verify_hs256, _base64url_decode
from app.tasks import FASTAPI_TASK_REGISTRY
from app.schemas import (
    DraftAnswersRequest, DraftAnswersResponse, ScreenQuestionDraft,
    ApplicationSubmitRequest, ApplicationSubmitResponse
)
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.services.llm_client import llm_client_general as llm_client
from app.database import get_db
from app.utils import clean_uuid
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        logger.info(f"WebSocket client connected to task {task_id}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket client disconnected from task {task_id}")

    async def broadcast(self, task_id: str, message: str):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.debug(f"Failed to send websocket message: {e}")

manager = ConnectionManager()

# --- Inline Request Models for Screening Answers ---
class SaveScreeningRequest(BaseModel):
    user_id: str
    question: str
    answer: str

class SearchScreeningRequest(BaseModel):
    user_id: str
    question: str

class UpdateAppStatusRequest(BaseModel):
    application_id: str
    status: str

# --- Endpoints ---

@router.post("/apply/draft", response_model=DraftAnswersResponse, tags=["apply"])
async def draft_answers(payload: DraftAnswersRequest, user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
    """
    Draft answers to job screening questions using Gemini 3.0/3.5 models.
    Supports both authenticated users and guest/preview workflows.
    """
    target_user_id = None
    if payload.user_id:
        sanitized_id = sanitize_user_id(payload.user_id)
        if sanitized_id:
            # If user is authenticated, ensure they can only query their own data
            if user and user.user_id:
                if clean_uuid(user.user_id) == clean_uuid(sanitized_id):
                    target_user_id = sanitized_id
            else:
                target_user_id = sanitized_id

    # 1. Lookup candidate profile from database
    profile_data = None
    if target_user_id:
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (target_user_id,))
                        row = await cur.fetchone()
                        if row:
                            profile_data = row[0]
        except Exception as e:
            logger.warning(f"Database lookup failed for profile {target_user_id}: {e}")

    # Fallback to mock profile if DB offline or empty
    if not profile_data:
        logger.info("Using fallback profile for screening question drafting.")
        profile_data = {
            "name": "Candidate",
            "email": "user@placeholder.local",
            "phone": "",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Tailwind CSS"],
            "experience": [
                {
                    "role": "Software Engineer",
                    "company": "TechCorp",
                    "start_date": "2023-01",
                    "end_date": "Present",
                    "bullets": ["Developed and maintained backend services using Python and FastAPI."]
                }
            ],
            "education": [
                {
                    "school": "University",
                    "degree": "B.S. Computer Science",
                    "date": "2023"
                }
            ],
            "projects": []
        }

    # 2. Lookup job listing from database
    job_data = None
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT title, company, location, remote, jd_text FROM jobs WHERE id = %s;", (payload.job_id,))
                    row = await cur.fetchone()
                    if row:
                        job_data = {
                            "title": row[0],
                            "company": row[1],
                            "location": row[2],
                            "remote": row[3],
                            "jd_text": row[4]
                        }
    except Exception as e:
        logger.warning(f"Database lookup failed for job {payload.job_id}: {e}")

    # Fallback search in memory cache if database lookup yields nothing
    if not job_data:
        logger.info("Using fallback job for screening question drafting.")
        from app.services.job_service import IN_MEMORY_JOB_CACHE
        found_job = None
        for query_hash in IN_MEMORY_JOB_CACHE:
            jobs_list = IN_MEMORY_JOB_CACHE[query_hash]
            # TTLCache can hold list or dict. Handle safely.
            if isinstance(jobs_list, tuple):
                jobs_list = jobs_list[0]
            elif hasattr(jobs_list, "get"):
                jobs_list = jobs_list.get("jobs", [])
            for job in jobs_list:
                if job.get("job_id") == payload.job_id:
                    found_job = job
                    break
            if found_job:
                break
        if found_job:
            job_data = {
                "title": found_job["title"],
                "company": found_job["company"],
                "location": found_job["location"],
                "remote": found_job["remote"],
                "jd_text": found_job["jd_text"]
            }
        else:
            job_data = {
                "title": "Python Backend Engineer",
                "company": "TechCorp",
                "location": "Karachi, Pakistan",
                "remote": False,
                "jd_text": "We are seeking a Python Backend Developer with strong knowledge of FastAPI and PostgreSQL."
            }

    # 3. Call Gemini to draft answers
    class LLMQuestionDraft(BaseModel):
        question_text: str = Field(..., description="The screening question text")
        drafted_answer: str = Field(..., description="Drafted professional, truthful answer")
        confidence: float = Field(..., description="Value between 0.0 and 1.0 indicating AI confidence")
        needs_user_input: bool = Field(..., description="True if answer is missing or uncertain")
        warning_message: Optional[str] = Field(None, description="Explanation for low confidence or warnings")

    class LLMScreeningDraftResponse(BaseModel):
        questions: List[LLMQuestionDraft]

    system_instruction = (
        "You are an expert recruiting assistant. Your goal is to draft truthful, accurate, "
        "and personalized answers to typical screening questions for a job application based "
        "on the candidate's resume profile. Do not fabricate or invent any details. If details "
        "are not found in the resume, explicitly set confidence < 0.5 and needs_user_input = True."
    )

    prompt = (
        "Please analyze the following job description and candidate profile. Then draft exactly 4 "
        "standard screening questions and answers:\n"
        "1. One question about experience with a primary technical skill in the JD.\n"
        "2. One question about work authorization / visa sponsorship.\n"
        "3. One question about expected salary or salary expectations.\n"
        "4. One question about notice period or availability.\n\n"
        "Use the candidate's actual profile details to draft the answers. Set confidence and needs_user_input:\n"
        "- If the answer is found in the resume, set confidence to 0.9+ and needs_user_input = False.\n"
        "- If the answer is not in the resume (such as notice period, expected salary, or visa sponsorship), "
        "draft a generic placeholder (e.g. 'To be negotiated', 'None required', etc.), set confidence to 0.3, "
        "set needs_user_input = True, and add a warning message explaining that this was not found in the resume.\n\n"
        "--- JOB DETAILS ---\n"
        f"Title: {job_data['title']}\n"
        f"Company: {job_data['company']}\n"
        f"Location: {job_data['location']}\n"
        f"Remote: {job_data['remote']}\n"
        f"Description: {job_data['jd_text']}\n\n"
        "--- CANDIDATE PROFILE ---\n"
        f"{json.dumps(profile_data)}\n"
    )

    try:
        # Task 2.1: Async LLM call to avoid blocking the event loop
        res = await llm_client.generate_structured_async(
            prompt=prompt,
            response_schema=LLMScreeningDraftResponse,
            model_type="flash",
            system_instruction=system_instruction
        )
        
        final_questions = []
        for idx, q in enumerate(res.questions):
            final_questions.append(
                ScreenQuestionDraft(
                    question_id=f"q{idx+1}",
                    question_text=q.question_text,
                    drafted_answer=q.drafted_answer,
                    confidence=q.confidence,
                    needs_user_input=q.needs_user_input,
                    warning_message=q.warning_message
                )
            )
        
        return DraftAnswersResponse(
            job_id=payload.job_id,
            questions=final_questions
        )
    except Exception as e:
        logger.error(f"Error drafting screening answers: {e}")
        # Safe fallback in case LLM fails completely
        return DraftAnswersResponse(
            job_id=payload.job_id,
            questions=[
                ScreenQuestionDraft(
                    question_id="q1",
                    question_text="How many years of experience do you have with FastAPI?",
                    drafted_answer="I have 2 years of experience building production APIs with FastAPI.",
                    confidence=0.95,
                    needs_user_input=False
                ),
                ScreenQuestionDraft(
                    question_id="q2",
                    question_text="What is your expected salary?",
                    drafted_answer="To be negotiated based on full compensation package.",
                    confidence=0.3,
                    needs_user_input=True,
                    warning_message="Salary expectations not specified in resume."
                )
            ]
        )

from cachetools import TTLCache
IDEMPOTENCY_CACHE = TTLCache(maxsize=1000, ttl=86400)

@router.post("/apply/submit", response_model=ApplicationSubmitResponse, tags=["apply"])
@limiter.limit("5/minute")
async def submit_application(
    request: Request,
    payload: ApplicationSubmitRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submit job application or trigger auto-apply agent.
    Performs duplicate detection and records to database.
    """
    idempotency_key = request.headers.get("X-Idempotency-Key") or request.headers.get("x-idempotency-key")
    if idempotency_key and idempotency_key in IDEMPOTENCY_CACHE:
        logger.info(f"Serving cached application response for key: {idempotency_key}")
        return ApplicationSubmitResponse.model_validate(IDEMPOTENCY_CACHE[idempotency_key])

    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to submit applications for this user"
        )
    payload.user_id = sanitized_id
    if payload.answers:
        payload.answers = {k: sanitize_text_input(v, field_name=f"answer_{k}") for k, v in payload.answers.items()}

    # 1. Retrieve job_hash and apply_url from database
    job_hash = None
    apply_url = None
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT job_hash, apply_url FROM jobs WHERE id = %s;", (payload.job_id,))
                    row = await cur.fetchone()
                    if row:
                        job_hash = row[0]
                        apply_url = row[1]
    except Exception as e:
        logger.warning(f"Database lookup failed for job {payload.job_id}: {e}")

    # Fallback to cache search
    if not job_hash:
        from app.services.job_service import IN_MEMORY_JOB_CACHE
        for query_hash in IN_MEMORY_JOB_CACHE:
            jobs_list = IN_MEMORY_JOB_CACHE[query_hash]
            if isinstance(jobs_list, tuple):
                jobs_list = jobs_list[0]
            elif hasattr(jobs_list, "get"):
                jobs_list = jobs_list.get("jobs", [])
            for job in jobs_list:
                if job.get("job_id") == payload.job_id:
                    job_hash = job.get("job_hash")
                    apply_url = job.get("apply_url")
                    break
            if job_hash:
                break
        if not job_hash:
            # Fallback generated hash
            job_hash = hashlib.sha256(payload.job_id.encode()).hexdigest()

    # If apply_url is relative, make it absolute using local backend port
    if apply_url and apply_url.startswith("/"):
        apply_url = f"http://localhost:{settings.BACKEND_PORT}{apply_url}"

    # 2. Check for duplicate application and retrieve profile/jd_text for quality scoring gate
    already_applied = False
    profile = None
    jd_text = ""
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT id FROM applications WHERE user_id = %s AND job_hash = %s;",
                        (payload.user_id, job_hash)
                    )
                    row = await cur.fetchone()
                    if row:
                        already_applied = True
                        
                    await cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (payload.user_id,))
                    row_p = await cur.fetchone()
                    if row_p and row_p[0]:
                        from app.schemas import ResumeParsedData
                        profile = ResumeParsedData.model_validate(row_p[0])
                        
                    await cur.execute("SELECT jd_text FROM jobs WHERE id = %s;", (payload.job_id,))
                    row_j = await cur.fetchone()
                    if row_j:
                        jd_text = row_j[0]
    except Exception as e:
        logger.warning(f"Database check failed for duplicate/quality checks: {e}")

    if already_applied:
        return ApplicationSubmitResponse(
            application_id=str(uuid.uuid4()),
            status="success",
            action_required=None
        )

    # Pre-submission quality gate check
    if profile and jd_text:
        from app.services.job_service import get_years_experience, extract_required_years
        from app.services.quality_scorer import QualityScorer
        
        # Calculate skills matched vs missing
        skills_matched = []
        skills_missing = []
        skills_lower = [s.lower() for s in profile.skills]
        jd_lower = jd_text.lower()
        for skill in profile.skills:
            if skill.lower() in jd_lower:
                skills_matched.append(skill)
                
        tech_words = {"python", "fastapi", "django", "react", "typescript", "kubernetes", "docker", "aws", "postgresql", "node.js", "java", "c++", "go", "rust", "terraform", "sql", "git", "ci/cd", "redis", "mongodb"}
        for word in tech_words:
            if word in jd_lower and word not in skills_lower:
                skills_missing.append(word.capitalize())
                
        candidate_years_exp = get_years_experience(profile)
        required_years_exp = extract_required_years(jd_text)
        
        quality = QualityScorer.calculate_quality(
            skills_matched=skills_matched,
            skills_missing=skills_missing,
            candidate_years_exp=candidate_years_exp,
            required_years_exp=required_years_exp,
            has_cover_letter=False,
            cl_text=""
        )
        
        logger.info(f"Pre-submission Quality Score: {quality.overall}")
        if quality.overall < 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application quality score ({quality.overall}) is below the required threshold of 30. Missing requirements: {', '.join(quality.missing_requirements)}."
            )

    # 3. Handle Tier-2 Browser Agent Auto-Apply Opt-in (Asynchronous Background Task)
    if payload.opt_in_agent:
        logger.info("Auto-apply agent requested as background task.")

        if not profile:
            from app.schemas import ResumeParsedData
            fallback_profile_dict = {
                "name": "Candidate",
                "email": "user@placeholder.local",
                "phone": "",
                "links": [],
                "education": [],
                "experience": [],
                "skills": [],
                "projects": [],
                "anchor_line": "Software Engineer",
                "highlights_strip": []
            }
            profile = ResumeParsedData.model_validate(fallback_profile_dict)

        target_url = apply_url or f"http://localhost:{settings.BACKEND_PORT}/mock-apply-form"
        # Dispatch persistent background task
        from app.tasks import add_persistent_task, celery_apply_task, redis_available
        task_payload = {
            "job_id": payload.job_id,
            "job_hash": job_hash,
            "apply_url": target_url,
            "profile_dict": profile.model_dump(),
            "answers": payload.answers
        }
        
        if redis_available and celery_apply_task:
            try:
                celery_task = celery_apply_task.delay(
                    payload.user_id,
                    payload.job_id,
                    job_hash,
                    target_url,
                    profile.model_dump(),
                    payload.answers
                )
                task_id = celery_task.id
                async with get_db() as conn:
                    if conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """
                                INSERT INTO background_tasks (id, user_id, task_type, status, payload, logs)
                                VALUES (%s, %s, %s, 'pending', %s, %s);
                                """,
                                (task_id, clean_uuid(payload.user_id), "auto_apply", json.dumps(task_payload), ["Task registered in Celery queue."])
                            )
                            await conn.commit()
            except Exception as celery_err:
                logger.warning(f"Failed to queue with Celery, falling back to persistent task: {celery_err}")
                task_id = await add_persistent_task(payload.user_id, "auto_apply", task_payload, priority=0)
        else:
            task_id = await add_persistent_task(payload.user_id, "auto_apply", task_payload, priority=0)
        
        response = ApplicationSubmitResponse(
            application_id=task_id,
            status="running",
            action_required=None
        )
        if idempotency_key:
            IDEMPOTENCY_CACHE[idempotency_key] = response.model_dump()
        return response

    # 4. Standard synchronous save if agent not used
    application_id = str(uuid.uuid4())
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO applications (id, user_id, job_id, job_hash, status)
                        VALUES (%s, %s, %s, %s, 'applied');
                        """,
                        (application_id, payload.user_id, payload.job_id, job_hash)
                    )
                    await conn.commit()
    except Exception as e:
        logger.error(f"Failed to save manual application to database: {e}")

    response = ApplicationSubmitResponse(
        application_id=application_id,
        status="success",
        action_required=None
    )
    if idempotency_key:
        IDEMPOTENCY_CACHE[idempotency_key] = response.model_dump()
    return response

@router.get("/api/applications/{user_id}", tags=["apply"])
async def get_user_applications(user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve all job applications tracked for a user, with local file fallback support."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this resource"
        )
    uid = clean_uuid(sanitized_id)
    apps_list = []
    
    # 1. Try DB first
    db_success = False
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT a.id, a.status, a.applied_at, j.id, j.title, j.company, j.location, j.source, j.apply_url
                        FROM applications a
                        JOIN jobs j ON a.job_id = j.id
                        WHERE a.user_id = %s
                        ORDER BY a.applied_at DESC;
                        """,
                        (uid,)
                    )
                    rows = await cur.fetchall()
                    for r in rows:
                        apps_list.append({
                            "id": str(r[0]),
                            "status": r[1],
                            "applied_at": r[2].isoformat() if r[2] else None,
                            "job_id": str(r[3]),
                            "title": r[4],
                            "company": r[5],
                            "location": r[6],
                            "source": r[7],
                            "apply_url": r[8]
                        })
                    db_success = True
    except Exception as e:
        logger.warning(f"DB applications lookup failed: {e}")
        
    # 2. Local fallback if DB is unreachable
    if not db_success:
        fallback_file = os.path.join(settings.DATA_DIR, "local_applications.json")
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    local_apps = json.load(f)
                    
                # Hydrate application job details from in-memory cache
                from app.services.job_service import IN_MEMORY_JOB_CACHE
                for app_rec in local_apps:
                    if app_rec.get("user_id") == uid:
                        # Find job details in cache
                        j_details = {"title": "Software Engineer", "company": "Tech Corp", "location": "Remote", "source": "LinkedIn", "apply_url": ""}
                        j_id = app_rec.get("job_id")
                        
                        found_job = False
                        for query_hash in IN_MEMORY_JOB_CACHE:
                            jobs_list = IN_MEMORY_JOB_CACHE[query_hash]
                            if isinstance(jobs_list, tuple):
                                jobs_list = jobs_list[0]
                            elif hasattr(jobs_list, "get"):
                                jobs_list = jobs_list.get("jobs", [])
                            for job in jobs_list:
                                if job.get("job_id") == j_id:
                                    j_details = {
                                        "title": job.get("title"),
                                        "company": job.get("company"),
                                        "location": job.get("location"),
                                        "source": job.get("source"),
                                        "apply_url": job.get("apply_url")
                                    }
                                    found_job = True
                                    break
                            if found_job:
                                break
                                
                        apps_list.append({
                            "id": app_rec.get("id"),
                            "status": app_rec.get("status", "applied"),
                            "applied_at": app_rec.get("applied_at", "2026-07-02T12:00:00"),
                            "job_id": j_id,
                            **j_details
                        })
            except Exception as f_err:
                logger.error(f"Failed to read local applications fallback file: {f_err}")
                
    return {"status": "success", "applications": apps_list}

@router.post("/api/applications/update-status", tags=["apply"])
async def update_application_status(payload: UpdateAppStatusRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Update application tracking status (e.g. from Kanban drag-and-drop)."""
    user_uuid = clean_uuid(user.user_id)
    
    # Check if the application belongs to the user
    db_checked = False
    belongs_to_user = False
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT user_id FROM applications WHERE id = %s;", (clean_uuid(payload.application_id),))
                    row = await cur.fetchone()
                    if row:
                        belongs_to_user = (clean_uuid(str(row[0])) == user_uuid)
                        db_checked = True
    except Exception as e:
        logger.warning(f"DB check failed for update status application check: {e}")
        
    if not db_checked:
        # Fallback local file check
        fallback_file = os.path.join(settings.DATA_DIR, "local_applications.json")
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    local_apps = json.load(f)
                for app_rec in local_apps:
                    if app_rec.get("id") == payload.application_id:
                        belongs_to_user = (clean_uuid(app_rec.get("user_id")) == user_uuid)
                        db_checked = True
                        break
            except Exception as f_err:
                logger.error(f"Failed to read local applications fallback: {f_err}")
                
    if db_checked and not belongs_to_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to modify this application"
        )

    db_success = False
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT status FROM applications WHERE id = %s;", (clean_uuid(payload.application_id),))
                    row = await cur.fetchone()
                    from_status = row[0] if row else None

                    await cur.execute(
                        "UPDATE applications SET status = %s WHERE id = %s;",
                        (payload.status, payload.application_id)
                    )

                    await cur.execute(
                        """
                        INSERT INTO application_events (application_id, event_type, from_status, to_status, actor, payload)
                        VALUES (%s, 'status_change', %s, %s, 'user', %s);
                        """,
                        (payload.application_id, from_status, payload.status, json.dumps({"reason": "Kanban drag-and-drop"}))
                    )
                    await conn.commit()
                    db_success = True
    except Exception as e:
        logger.warning(f"DB update application status failed: {e}")
        
    if not db_success:
        # Local fallback updates
        fallback_file = os.path.join(settings.DATA_DIR, "local_applications.json")
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    local_apps = json.load(f)
                for app_rec in local_apps:
                    if app_rec.get("id") == payload.application_id:
                        app_rec["status"] = payload.status
                with open(fallback_file, "w", encoding="utf-8") as f:
                    json.dump(local_apps, f)
            except Exception as f_err:
                logger.error(f"Failed to update local applications fallback: {f_err}")
                raise HTTPException(status_code=500, detail="Failed to update local application record.")
                
    return {"status": "success", "message": "Application status updated!"}

@router.get("/api/apply/status/{task_id}", tags=["apply"])
async def get_apply_task_status(task_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve current background task execution status."""
    from app.tasks import FASTAPI_TASK_REGISTRY
    uid = clean_uuid(user.user_id)
    
    # 1. Check database first for persistent reboot-safe status
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT status, result, logs, error, user_id FROM background_tasks WHERE id = %s;",
                        (clean_uuid(task_id),)
                    )
                    row = await cur.fetchone()
                    if row:
                        status_val, result_val, logs_val, error_val, task_owner = row
                        if clean_uuid(str(task_owner)) != uid:
                            raise HTTPException(status_code=403, detail="Forbidden")
                        
                        action_required = None
                        if status_val == "needs_action" and isinstance(result_val, dict):
                            action_required = result_val.get("action_required")
                        return {
                            "status": status_val,
                            "action_required": action_required,
                            "error": error_val,
                            "logs": logs_val or []
                        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Database task lookup failed: {e}")

    # 2. Fallback to in-memory registry
    if task_id in FASTAPI_TASK_REGISTRY:
        task_data = FASTAPI_TASK_REGISTRY[task_id]
        task_owner = task_data.get("user_id")
        if task_owner and clean_uuid(user.user_id) != clean_uuid(task_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access this task status"
            )
        return {
            "status": task_data.get("status", "running"),
            "action_required": task_data.get("action_required"),
            "error": task_data.get("error"),
            "logs": task_data.get("logs", [])
        }
    return {"status": "pending", "action_required": None}

@router.post("/api/screening/save", tags=["apply"])
@limiter.limit("15/minute")
async def api_save_screening_answer(request: Request, payload: SaveScreeningRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Save a screening answer to the candidate's memory bank."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to manage screening answers for this user"
        )
    payload.user_id = sanitized_id
    if payload.question:
        payload.question = sanitize_text_input(payload.question, max_length=1000, field_name="question")
    if payload.answer:
        payload.answer = sanitize_text_input(payload.answer, max_length=5000, field_name="answer")

    from app.services.screening_kb import save_screening_answer
    success = save_screening_answer(payload.user_id, payload.question, payload.answer)
    return {"status": "success", "success": success}

@router.post("/api/screening/search", tags=["apply"])
@limiter.limit("20/minute")
async def api_search_screening_answer(request: Request, payload: SearchScreeningRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Semantically search matching screening answers in user memory bank."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to search screening answers for this user"
        )
    payload.user_id = sanitized_id
    if payload.question:
        payload.question = sanitize_text_input(payload.question, max_length=1000, field_name="question")

    from app.services.screening_kb import search_screening_answer
    answer = search_screening_answer(payload.user_id, payload.question)
    return {"status": "success", "answer": answer}

@router.websocket("/api/ws/apply/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, token: Optional[str] = None, dev_user_id: Optional[str] = None):
    # Verify token or dev_user_id against the task's user_id if task exists in registry
    user = None
    if SUPABASE_JWT_SECRET:
        if token:
            try:
                payload = _verify_hs256(token, SUPABASE_JWT_SECRET)
                user = AuthenticatedUser(
                    user_id=payload.get("sub"),
                    email=payload.get("email"),
                    role=payload.get("role", "user")
                )
            except Exception as e:
                logger.warning(f"WebSocket JWT validation failed: {e}")
                await websocket.accept()
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
    else:
        if token:
            try:
                parts = token.split(".")
                if len(parts) == 3:
                    payload = json.loads(_base64url_decode(parts[1]))
                    user = AuthenticatedUser(
                        user_id=payload.get("sub"),
                        email=payload.get("email"),
                        role=payload.get("role", "user")
                    )
            except Exception:
                pass
        if not user and dev_user_id:
            user = AuthenticatedUser(user_id=dev_user_id, email="dev@localhost")
            
    if task_id in FASTAPI_TASK_REGISTRY:
        task_data = FASTAPI_TASK_REGISTRY[task_id]
        task_owner = task_data.get("user_id")
        if task_owner:
            if not user or clean_uuid(user.user_id) != clean_uuid(task_owner):
                logger.warning(f"Unauthorized websocket attempt for task {task_id}")
                await websocket.accept()
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

    await manager.connect(task_id, websocket)
    try:
        # Buffer dump fallback if task is already running in background
        if task_id in FASTAPI_TASK_REGISTRY:
            for log in FASTAPI_TASK_REGISTRY[task_id].get("logs", []):
                await websocket.send_text(log)
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket execution error for task {task_id}: {e}")
        manager.disconnect(task_id, websocket)
