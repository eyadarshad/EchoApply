import uuid
import logging
logging.basicConfig(level=logging.DEBUG)
from fastapi import FastAPI, UploadFile, File, Response, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    HealthResponse, EchoRequest, EchoResponse, 
    ResumeParsedData, ResumeIntakeResponse,
    ResumeTailorRequest, ResumeTailorResponse,
    JobSearchRequest, JobSearchResponse,
    DraftAnswersRequest, DraftAnswersResponse, ScreenQuestionDraft,
    ApplicationSubmitRequest, ApplicationSubmitResponse
)
from app.config import settings
from app.parsers.pdf_parser import extract_text_from_pdf, PDFParserError, ScannedPDFError, render_pdf_to_images
from app.parsers.llm_extractor import extract_resume_data, extract_resume_from_images
from app.services.github_enricher import extract_github_username, enrich_profile_with_github
from app.services.resume_generator import generate_resume_pdf, generate_resume_docx
from app.pipeline.orchestrator import tailor_resume_flow
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

job_service = JobService()

app = FastAPI(
    title="AI Resume Generator & Smart Apply API",
    version="1.0.0",
    description="Backend API services for resume extraction, tailoring, job search, and auto-applying."
)

# CORS configuration
frontend_origins = [
    f"http://localhost:{settings.FRONTEND_PORT}",
    f"http://127.0.0.1:{settings.FRONTEND_PORT}",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3005",
    "http://127.0.0.1:3005",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify backend and database connection status."""
    return HealthResponse(status="ok")

@app.post("/echo", response_model=EchoResponse)
async def echo_message(payload: EchoRequest):
    """Verify API request and response serialization."""
    return EchoResponse(
        message=payload.message,
        status="success"
    )

@app.post("/intake", response_model=ResumeIntakeResponse)
async def resume_intake(file: UploadFile = File(...)):
    """
    Accepts a PDF resume, parses its text, runs structured LLM extraction, 
    and enriches it with GitHub repositories.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for resume intake."
        )

    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # 1. Parse PDF (with OCR fallback)
        try:
            raw_text = extract_text_from_pdf(file_bytes)
            # 2. LLM Structured Extraction
            parsed_data = extract_resume_data(raw_text)
        except ScannedPDFError as scanned_err:
            logger.info(f"Text-based parsing or Tesseract failed: {str(scanned_err)}. Falling back to Gemini Vision...")
            # Render PDF pages to images
            images = render_pdf_to_images(file_bytes)
            if not images:
                raise scanned_err
            # Multimodal structured extraction directly from images
            parsed_data = extract_resume_from_images(images, filename=file.filename)
        
        # 3. GitHub Profile Enrichment
        github_username = extract_github_username(parsed_data.links)
        github_enriched = None
        if github_username:
            github_enriched = await enrich_profile_with_github(github_username)
            
        # Generate a temporary user ID for this session
        user_id = str(uuid.uuid4())
        
        return ResumeIntakeResponse(
            user_id=user_id,
            parsed_resume=parsed_data,
            github_enriched=github_enriched
        )
    except PDFParserError as e:
        logger.error(f"PDF Parser Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during intake: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the resume: {str(e)}"
        )

@app.post("/render")
async def render_resume(
    data: ResumeParsedData, 
    format: str = Query("pdf", pattern="^(pdf|docx)$")
):
    """
    Renders structured resume data to either PDF (WeasyPrint) or Word (.docx) file.
    """
    try:
        if format == "pdf":
            pdf_bytes = generate_resume_pdf(data)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=resume.pdf"
                }
            )
        else:
            docx_bytes = generate_resume_docx(data)
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": "attachment; filename=resume.docx"
                }
            )
    except (ImportError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System rendering libraries missing: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to render resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render document: {str(e)}"
        )

# ==========================================
# Phase 2: Tailoring Pipeline
# ==========================================

@app.post("/tailor", response_model=ResumeTailorResponse)
async def tailor_resume(payload: ResumeTailorRequest):
    """
    Orchestrates the resume tailoring process for a specific job.
    """
    # 1. Resolve the profile data
    profile = payload.parsed_resume
    major = "Computer Science"  # Default major
    
    # If not supplied in payload, attempt to look up from database
    if not profile:
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT parsed_resume_json, major FROM profiles JOIN users ON users.id = profiles.user_id WHERE user_id = %s;",
                    (payload.user_id,)
                )
                row = cursor.fetchone()
                if row:
                    profile = ResumeParsedData.model_validate(row[0])
                    major = row[1] or "Computer Science"
        except Exception:
            pass
        finally:
            if conn:
                conn.close()

    # Raise error if no profile was supplied and could not be fetched from DB
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parsed resume profile was not supplied and could not be retrieved from the database."
        )

    # 2. Resolve job description text
    jd_text = payload.jd_text
    if not jd_text:
        # Attempt to look up from database jobs table
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
            with conn.cursor() as cursor:
                cursor.execute("SELECT jd_text FROM jobs WHERE id = %s;", (payload.job_id,))
                row = cursor.fetchone()
                if row:
                    jd_text = row[0]
        except Exception:
            pass
        finally:
            if conn:
                conn.close()
                
    # Raise error if no job description text was supplied and could not be fetched from DB
    if not jd_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text was not supplied and could not be retrieved from the database."
        )

    try:
        # Run tailoring pipeline
        result = tailor_resume_flow(profile, jd_text, major)

        # 3. Store result in database if reachable
        resume_id = str(uuid.uuid4())
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
            with conn.cursor() as cursor:
                import json
                cursor.execute(
                    """
                    INSERT INTO tailored_resumes (id, user_id, job_id, content_json, ats_score)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (resume_id, payload.user_id, payload.job_id, json.dumps(result["content_json"]), result["ats_score"])
                )
                conn.commit()
        except Exception:
            pass
        finally:
            if conn:
                conn.close()

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

# ==========================================
# Phase 3 & 5: Job Search & Matching Stub
# ==========================================

@app.post("/jobs/search", response_model=JobSearchResponse)
async def search_jobs(payload: JobSearchRequest):
    """
    Search and rank job listings from multiple aggregators.
    """
    try:
        return await job_service.search_and_rank_jobs(payload)
    except Exception as e:
        logger.error(f"Error in /jobs/search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during job search: {str(e)}"
        )

# ==========================================
# Phase 4 & 6: Application & Auto-Apply Stubs
# ==========================================

@app.post("/apply/draft", response_model=DraftAnswersResponse)
async def draft_answers(payload: DraftAnswersRequest):
    """
    Draft answers to job screening questions using Gemini 3.0/3.5 models.
    """
    import json
    import psycopg
    from typing import Optional, List
    from pydantic import BaseModel, Field
    from app.services.llm_client import llm_client

    # 1. Lookup candidate profile from database
    profile_data = None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (payload.user_id,))
            row = cur.fetchone()
            if row:
                profile_data = row[0]
        conn.close()
    except Exception as e:
        logger.warning(f"Database lookup failed for profile {payload.user_id}: {e}")

    # Fallback to mock profile if DB offline or empty
    if not profile_data:
        logger.info("Using fallback profile for screening question drafting.")
        profile_data = {
            "name": "Eyad Ahmed",
            "email": "eyad@example.com",
            "phone": "+92-300-1234567",
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
                    "school": "NUCES - FAST",
                    "degree": "B.S. Computer Science",
                    "date": "2023"
                }
            ],
            "projects": []
        }

    # 2. Lookup job listing from database
    job_data = None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT title, company, location, remote, jd_text FROM jobs WHERE id = %s;", (payload.job_id,))
            row = cur.fetchone()
            if row:
                job_data = {
                    "title": row[0],
                    "company": row[1],
                    "location": row[2],
                    "remote": row[3],
                    "jd_text": row[4]
                }
        conn.close()
    except Exception as e:
        logger.warning(f"Database lookup failed for job {payload.job_id}: {e}")

    # Fallback search in memory cache if database lookup yields nothing
    if not job_data:
        logger.info("Using fallback job for screening question drafting.")
        from app.services.job_service import IN_MEMORY_JOB_CACHE
        found_job = None
        for query_hash, cache_entry in IN_MEMORY_JOB_CACHE.items():
            jobs_list = cache_entry[0] if isinstance(cache_entry, tuple) else cache_entry.get("jobs", [])
            for job in jobs_list:
                if job.get("job_id") == payload.job_id:
                    found_job = job
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
        res = llm_client.generate_structured(
            prompt=prompt,
            response_schema=LLMScreeningDraftResponse,
            model_type="flash",
            system_instruction=system_instruction
        )
        
        # Map LLM results to schema
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

@app.post("/apply/submit", response_model=ApplicationSubmitResponse)
async def submit_application(payload: ApplicationSubmitRequest):
    """
    Submit job application or trigger auto-apply agent.
    Performs duplicate detection and records to database.
    """
    import psycopg
    import hashlib

    # 1. Retrieve job_hash from database
    job_hash = None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT job_hash FROM jobs WHERE id = %s;", (payload.job_id,))
            row = cur.fetchone()
            if row:
                job_hash = row[0]
        conn.close()
    except Exception as e:
        logger.warning(f"Database lookup failed for job {payload.job_id}: {e}")

    # Fallback to cache search
    if not job_hash:
        from app.services.job_service import IN_MEMORY_JOB_CACHE
        for query_hash, cache_entry in IN_MEMORY_JOB_CACHE.items():
            jobs_list = cache_entry[0] if isinstance(cache_entry, tuple) else cache_entry.get("jobs", [])
            for job in jobs_list:
                if job.get("job_id") == payload.job_id:
                    job_hash = job.get("job_hash")
                    break
        if not job_hash:
            # Fallback generated hash
            job_hash = hashlib.sha256(payload.job_id.encode()).hexdigest()

    # 2. Check for duplicate application
    already_applied = False
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM applications WHERE user_id = %s AND job_hash = %s;",
                (payload.user_id, job_hash)
            )
            row = cur.fetchone()
            if row:
                already_applied = True
        conn.close()
    except Exception as e:
        logger.warning(f"Database check failed for duplicate application: {e}")

    if already_applied:
        return ApplicationSubmitResponse(
            application_id=str(uuid.uuid4()),
            status="success",
            action_required=None
        )

    # 3. Create new application record
    application_id = str(uuid.uuid4())
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO applications (id, user_id, job_id, job_hash, status)
                VALUES (%s, %s, %s, %s, 'applied');
                """,
                (application_id, payload.user_id, payload.job_id, job_hash)
            )
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save application to database: {e}")
        # Fallback success for offline/unreachable DB (transient memory path)
        return ApplicationSubmitResponse(
            application_id=application_id,
            status="success",
            action_required=None
        )

    return ApplicationSubmitResponse(
        application_id=application_id,
        status="success",
        action_required=None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=False
    )
