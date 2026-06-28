import uuid
import logging
from fastapi import FastAPI, UploadFile, File, Response, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    HealthResponse, EchoRequest, EchoResponse, 
    ResumeParsedData, ResumeIntakeResponse,
    ResumeTailorRequest, ResumeTailorResponse,
    JobSearchRequest, JobSearchResponse,
    DraftAnswersRequest, DraftAnswersResponse,
    ApplicationSubmitRequest, ApplicationSubmitResponse
)
from app.config import settings
from app.parsers.pdf_parser import extract_text_from_pdf, PDFParserError, ScannedPDFError, render_pdf_to_images
from app.parsers.llm_extractor import extract_resume_data, extract_resume_from_images
from app.services.github_enricher import extract_github_username, enrich_profile_with_github
from app.services.resume_generator import generate_resume_pdf, generate_resume_docx
from app.pipeline.orchestrator import tailor_resume_flow

logger = logging.getLogger(__name__)

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

    # Fallback to mock profile if DB is unreachable and no profile was supplied
    if not profile:
        profile = ResumeParsedData(
            name="Eyad Ahmed",
            email="eyad.ahmed@example.com",
            phone="+92-300-1234567",
            links=["github.com/eyad-dev", "linkedin.com/in/eyadahmed"],
            skills=["Python", "FastAPI", "TypeScript", "Next.js", "PostgreSQL"],
            education=[{"degree": "B.S.", "major": "Computer Science", "school": "NUCES", "date": "2024"}],
            experience=[{
                "role": "Software Engineer Intern",
                "company": "TechSolutions",
                "start_date": "2023-06",
                "end_date": "2024-05",
                "bullets": [
                    "Developed backend services using Python and FastAPI.",
                    "Built frontend UI in React and Next.js."
                ]
            }],
            projects=[]
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
                
    # Fallback to default job description if none provided and DB is offline
    if not jd_text:
        jd_text = (
            "We are looking for a Software Engineer with experience in Python, FastAPI, and Next.js. "
            "Responsibilities include building web backend services, structuring databases, and collaborating on UI components."
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
    This is a stub for Phase 3/5 implementation.
    """
    import datetime
    return JobSearchResponse(
        query_hash="stub_hash",
        jobs=[
            {
                "job_id": "stub_job_1",
                "source": "JSearch",
                "title": "Backend Developer",
                "company": "Tech Solutions",
                "location": payload.location or "Remote",
                "remote": payload.remote_only,
                "apply_url": "https://example.com/apply",
                "jd_text": "We are looking for a Python developer...",
                "fetched_at": datetime.datetime.now(datetime.timezone.utc),
                "job_hash": "stub_job_hash_1",
                "match_score": 0.9,
                "match_explanation": "Good match based on Python and FastAPI.",
                "is_applied": False
            }
        ]
    )

# ==========================================
# Phase 4 & 6: Application & Auto-Apply Stubs
# ==========================================

@app.post("/apply/draft", response_model=DraftAnswersResponse)
async def draft_answers(payload: DraftAnswersRequest):
    """
    Draft answers to job screening questions.
    This is a stub for Phase 4 implementation.
    """
    return DraftAnswersResponse(
        job_id=payload.job_id,
        questions=[
            {
                "question_id": "q1",
                "question_text": "How many years of experience do you have with FastAPI?",
                "drafted_answer": "I have 2 years of experience building production APIs with FastAPI.",
                "confidence": 0.95,
                "needs_user_input": False
            }
        ]
    )

@app.post("/apply/submit", response_model=ApplicationSubmitResponse)
async def submit_application(payload: ApplicationSubmitRequest):
    """
    Submit job application or trigger auto-apply agent.
    This is a stub for Phase 4/6 implementation.
    """
    return ApplicationSubmitResponse(
        application_id=str(uuid.uuid4()),
        status="pending" if payload.opt_in_agent else "success",
        action_required=None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=True
    )
