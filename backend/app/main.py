import uuid
import logging
logging.basicConfig(level=logging.DEBUG)
from fastapi import FastAPI, UploadFile, File, Response, Query, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    HealthResponse, EchoRequest, EchoResponse, 
    ResumeParsedData, ResumeIntakeResponse,
    ResumeTailorRequest, ResumeTailorResponse,
    JobSearchRequest, JobSearchResponse,
    DraftAnswersRequest, DraftAnswersResponse, ScreenQuestionDraft,
    ApplicationSubmitRequest, ApplicationSubmitResponse,
    SaveProfileRequest, SaveProfileResponse
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

def clean_uuid(user_id: str) -> str:
    """Helper to convert any transient user_id into a valid UUID string format."""
    if not user_id:
        return str(uuid.uuid4())
    try:
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))

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
        
        # Save to database and generate embedding
        from app.services.embedding_service import serialize_profile
        from app.services.llm_client import llm_client
        
        try:
            serialized_text = serialize_profile(parsed_data)
            embedding = llm_client.generate_embedding(serialized_text)
            
            import psycopg
            conn = None
            try:
                conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
                with conn.cursor() as cur:
                    import json
                    cur.execute(
                        """
                        INSERT INTO users (id, email, major)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        (user_id, parsed_data.email, "Computer Science")
                    )
                    cur.execute(
                        """
                        INSERT INTO profiles (user_id, parsed_resume_json, profile_embedding)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET parsed_resume_json = EXCLUDED.parsed_resume_json, 
                            profile_embedding = EXCLUDED.profile_embedding,
                            updated_at = NOW();
                        """,
                        (user_id, json.dumps(parsed_data.model_dump()), embedding)
                    )
                    conn.commit()
            except Exception as db_err:
                logger.warning(f"Failed to save intake profile to DB: {db_err}")
            finally:
                if conn:
                    conn.close()
        except Exception as embed_err:
            logger.warning(f"Failed to generate profile embedding: {embed_err}")
        
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

@app.post("/profiles", response_model=SaveProfileResponse)
async def save_profile(payload: SaveProfileRequest):
    """
    Saves or updates a candidate profile in the database,
    automatically generating and storing its semantic vector embedding.
    """
    user_id = clean_uuid(payload.user_id)
    profile = payload.parsed_resume
    major = payload.major or "Computer Science"
    
    from app.services.embedding_service import serialize_profile
    from app.services.llm_client import llm_client
    
    try:
        serialized_text = serialize_profile(profile)
        embedding = llm_client.generate_embedding(serialized_text)
    except Exception as embed_err:
        logger.warning(f"Failed to generate profile embedding: {embed_err}")
        embedding = [0.0] * 768
    
    import psycopg
    conn = None
    status_msg = "transient"
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
        with conn.cursor() as cur:
            import json
            cur.execute(
                """
                INSERT INTO users (id, email, major)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, major = EXCLUDED.major;
                """,
                (user_id, profile.email, major)
            )
            cur.execute(
                """
                INSERT INTO profiles (user_id, parsed_resume_json, profile_embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET parsed_resume_json = EXCLUDED.parsed_resume_json, 
                    profile_embedding = EXCLUDED.profile_embedding,
                    updated_at = NOW();
                """,
                (user_id, json.dumps(profile.model_dump()), embedding)
            )
            conn.commit()
        status_msg = "saved"
    except Exception as db_err:
        logger.warning(f"Failed to save profile {user_id} to DB: {db_err}")
    finally:
        if conn:
            conn.close()
            
    return SaveProfileResponse(
        user_id=user_id,
        status=status_msg
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

@app.get("/mock-apply-form", response_class=HTMLResponse)
async def mock_apply_form(
    login: bool = Query(False),
    captcha: bool = Query(False),
    unmapped: bool = Query(False)
):
    """
    Renders a mock job application form for local sandboxed testing of Playwright auto-apply.
    """
    if login:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Mock Job Board - Login</title></head>
        <body style="font-family: Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 40px; text-align: center;">
            <h1>Sign in to your account</h1>
            <form action="/mock-login-submit" method="POST" style="max-width: 300px; margin: 0 auto; text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label for="username" style="display:block; margin-bottom:5px;">Username</label>
                    <input type="text" id="username" name="username" required style="width:100%; padding:8px;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label for="password" style="display:block; margin-bottom:5px;">Password</label>
                    <input type="password" id="password" name="password" required style="width:100%; padding:8px;">
                </div>
                <button type="submit" style="background:#4f46e5; color:white; border:none; padding:10px 20px; cursor:pointer;">Log In</button>
            </form>
        </body>
        </html>
        """, status_code=200)
        
    if captcha:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Mock Job Board - Verification</title></head>
        <body style="font-family: Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 40px; text-align: center;">
            <h1>Verify you are human</h1>
            <p>Please complete the challenge below</p>
            <div style="max-width: 400px; margin: 20px auto; padding: 20px; border: 1px solid #334155;">
                <iframe src="about:blank" title="reCAPTCHA verification challenge" style="width: 300px; height: 80px; border:none; background:#1e293b;"></iframe>
                <form action="/mock-captcha-submit" method="POST" style="margin-top:15px; text-align: left;">
                    <div>
                        <label for="captcha" style="display:block; margin-bottom:5px;">Solve captcha *</label>
                        <input type="text" id="captcha" name="captcha" required style="width:100%; padding:8px;">
                    </div>
                    <button type="submit" style="background:#4f46e5; color:white; border:none; padding:10px 20px; margin-top:10px; cursor:pointer;">Verify & Submit</button>
                </form>
            </div>
        </body>
        </html>
        """, status_code=200)

    # Standard Mock Form
    unmapped_field_html = ""
    if unmapped:
        unmapped_field_html = """
        <div class="field">
            <label for="favorite_language">Favorite Coding Language *</label>
            <input type="text" id="favorite_language" name="favorite_language" required>
        </div>
        """

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Job Board - Application Form</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background: #0f172a; color: #f1f5f9; border: 1px solid #334155; border-radius: 12px; }}
            .field {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #94a3b8; }}
            input[type="text"], input[type="email"], input[type="tel"], input[type="url"], select, textarea {{
                width: 100%; padding: 10px; border: 1px solid #334155; border-radius: 8px; background: #1e293b; color: #f1f5f9; box-sizing: border-box;
            }}
            button {{ background: #4f46e5; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
            button:hover {{ background: #4338ca; }}
        </style>
    </head>
    <body>
        <h1 style="color: #6366f1;">Apply for Software Engineer</h1>
        <p style="color: #64748b; font-size: 14px; margin-bottom: 24px;">Please fill out the form below to submit your application.</p>
        <form action="/mock-apply-submit" method="POST">
            <div class="field">
                <label for="fullname">Full Name *</label>
                <input type="text" id="fullname" name="fullname" required>
            </div>
            
            <div class="field">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="field">
                <label for="phone">Phone Number</label>
                <input type="tel" id="phone" name="phone">
            </div>
            
            <div class="field">
                <label for="github">GitHub URL</label>
                <input type="url" id="github" name="github">
            </div>
            
            <div class="field">
                <label for="fastapi_exp">How many years of experience do you have with FastAPI? *</label>
                <textarea id="fastapi_exp" name="fastapi_exp" rows="3" required></textarea>
            </div>
            
            <div class="field">
                <label for="salary_exp">What is your expected salary? *</label>
                <input type="text" id="salary_exp" name="salary_exp" required>
            </div>
            
            <div class="field">
                <label for="terms_agree">
                    <input type="checkbox" id="terms_agree" name="terms_agree" required value="agree">
                    Do you agree to the terms of service? *
                </label>
            </div>
            
            {unmapped_field_html}
            
            <button type="submit">Submit Application</button>
        </form>
    </body>
    </html>
    """, status_code=200)

@app.post("/mock-apply-submit", response_class=HTMLResponse)
async def mock_apply_submit():
    """
    Handles form submission for local mock job board.
    """
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Mock Job Board - Success</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px; background: #0f172a; color: #f1f5f9;">
        <h1 style="color: #10b981;">Application Submitted Successfully!</h1>
        <p>Thank you for applying. We have received your application.</p>
    </body>
    </html>
    """, status_code=200)

@app.post("/apply/submit", response_model=ApplicationSubmitResponse)
async def submit_application(payload: ApplicationSubmitRequest):
    """
    Submit job application or trigger auto-apply agent.
    Performs duplicate detection and records to database.
    """
    import psycopg
    import hashlib

    # 1. Retrieve job_hash and apply_url from database
    job_hash = None
    apply_url = None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT job_hash, apply_url FROM jobs WHERE id = %s;", (payload.job_id,))
            row = cur.fetchone()
            if row:
                job_hash = row[0]
                apply_url = row[1]
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
                    apply_url = job.get("apply_url")
                    break
        if not job_hash:
            # Fallback generated hash
            job_hash = hashlib.sha256(payload.job_id.encode()).hexdigest()

    # If apply_url is relative, make it absolute using local backend port
    if apply_url and apply_url.startswith("/"):
        apply_url = f"http://localhost:{settings.BACKEND_PORT}{apply_url}"

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

    # 3. Handle Tier-2 Browser Agent Auto-Apply Opt-in
    action_required_info = None
    agent_status = "success"
    
    if payload.opt_in_agent:
        logger.info("Auto-apply agent requested.")
        # Retrieve candidate profile
        profile = None
        try:
            conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (payload.user_id,))
                row = cur.fetchone()
                if row:
                    from app.schemas import ResumeParsedData
                    profile = ResumeParsedData.model_validate(row[0])
            conn.close()
        except Exception as e:
            logger.warning(f"Database lookup failed for profile {payload.user_id}: {e}")

        if not profile:
            # Fallback profile
            from app.schemas import ResumeParsedData
            fallback_profile_dict = {
                "name": "Eyad Ahmed",
                "email": "eyad@example.com",
                "phone": "+92-300-1234567",
                "links": ["https://github.com/eyadahmed"],
                "education": [],
                "experience": [],
                "skills": [],
                "projects": [],
                "anchor_line": "Software Engineer",
                "highlights_strip": []
            }
            profile = ResumeParsedData.model_validate(fallback_profile_dict)

        target_url = apply_url or f"http://localhost:{settings.BACKEND_PORT}/mock-apply-form"
        logger.info(f"Triggering run_auto_apply_agent for URL: {target_url}")
        
        from app.services.browser_agent import run_auto_apply_agent
        agent_res = await run_auto_apply_agent(target_url, profile, payload.answers)
        
        if agent_res.get("status") == "needs_action":
            agent_status = "needs_action"
            action_required_info = agent_res.get("action_required")
            logger.info("Agent requires user action.")
        else:
            logger.info("Agent auto-applied successfully.")

    # 4. Create new application record if agent succeeded or wasn't used
    application_id = str(uuid.uuid4())
    if agent_status == "success":
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

    return ApplicationSubmitResponse(
        application_id=application_id,
        status="success" if agent_status == "success" else "needs_action",
        action_required=action_required_info
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=False
    )
