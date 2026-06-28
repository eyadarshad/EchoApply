import uuid
import logging
from fastapi import FastAPI, UploadFile, File, Response, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    HealthResponse, EchoRequest, EchoResponse, 
    ResumeParsedData, ResumeIntakeResponse
)
from app.config import settings
from app.parsers.pdf_parser import extract_text_from_pdf, PDFParserError, ScannedPDFError
from app.parsers.llm_extractor import extract_resume_data
from app.services.github_enricher import extract_github_username, enrich_profile_with_github
from app.services.resume_generator import generate_resume_pdf, generate_resume_docx

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Resume Generator & Smart Apply API",
    version="1.0.0",
    description="Backend API services for resume extraction, tailoring, job search, and auto-applying."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        raw_text = extract_text_from_pdf(file_bytes)
        
        # 2. LLM Structured Extraction
        parsed_data = extract_resume_data(raw_text)
        
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

    except ScannedPDFError as e:
        logger.error(f"Scanned PDF Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=True
    )
