import uuid
import logging
import json
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from app.limiter import limiter
from app.schemas import ResumeIntakeResponse, ResumeParsedData
from app.config import settings
from app.sanitize import sanitize_filename
from app.parsers.pdf_parser import extract_text_from_pdf, PDFParserError, ScannedPDFError, render_pdf_to_images
from app.parsers.llm_extractor import extract_resume_data, extract_resume_from_images
from app.services.github_enricher import extract_github_username
from app.services.embedding_service import serialize_profile
from app.services.llm_client import llm_client_resume as llm_client
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intake"])

@router.post("/intake", response_model=ResumeIntakeResponse)
@limiter.limit("10/minute")
async def resume_intake(request: Request, file: UploadFile = File(...)):
    """
    Accepts a PDF resume, parses its text, runs structured LLM extraction, 
    and enriches it with GitHub repositories.
    """
    sanitized_name = sanitize_filename(file.filename)
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
            parsed_data = extract_resume_from_images(images, filename=sanitized_name)
        
        # 3. GitHub Profile Enrichment
        github_username = extract_github_username(parsed_data.links)
        github_enriched = None
        if github_username:
            from app.main import enrich_profile_with_github
            github_enriched = await enrich_profile_with_github(github_username)
            
        # Generate a temporary user ID for this session
        user_id = str(uuid.uuid4())
        
        # Save to database and generate embedding
        try:
            serialized_text = serialize_profile(parsed_data)
            embedding = llm_client.generate_embedding(serialized_text)
            
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO users (id, email, major)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (id) DO NOTHING;
                            """,
                            (user_id, parsed_data.email, "Computer Science")
                        )
                        await cur.execute(
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
                        await conn.commit()
        except Exception as db_err:
            logger.warning(f"Failed to save intake profile or generate embedding: {db_err}")
        
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
