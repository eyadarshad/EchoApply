"""
Router for CV Audit and LinkedIn Profile Audit endpoints.
"""

import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, UploadFile, File, Form, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.auth import get_optional_user, AuthenticatedUser
from app.parsers.pdf_parser import extract_text_from_pdf, ScannedPDFError, render_pdf_to_images
from app.parsers.llm_extractor import extract_resume_from_images
from app.services.audit_engine import (
    audit_cv_comprehensive,
    audit_linkedin_comprehensive,
    AuditReportResponse,
)
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])

# In-memory history fallback for instant development/guest sessions
AUDIT_HISTORY_STORE: Dict[str, List[Dict[str, Any]]] = {}

# --- Request Models ---

class AuditCvJsonRequest(BaseModel):
    user_id: Optional[str] = None
    target_role: Optional[str] = "Software / AI Engineer"
    jd_text: Optional[str] = None
    resume_text: Optional[str] = None
    parsed_resume: Optional[Dict[str, Any]] = None

class AuditLinkedInJsonRequest(BaseModel):
    user_id: Optional[str] = None
    target_role: Optional[str] = "AI Engineer / Software Engineer"
    profile_text: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[str] = None

class AuditSaveRequest(BaseModel):
    user_id: str
    audit_type: str
    total_score: int
    max_score: int = 100
    quality_label: str
    dimensions: List[Dict[str, Any]]
    top_3_changes: List[Dict[str, Any]]
    target_role: Optional[str] = None

# --- Endpoints ---

@router.post("/cv", response_model=AuditReportResponse)
async def audit_cv_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    data_json: Optional[str] = Form(None),
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """
    Audits a candidate's CV/Resume across 25 ATS and quality criteria.
    Accepts either multipart file upload (PDF) or JSON payload.
    """
    raw_text = ""
    parsed_resume = None
    target_role = "Software / AI Engineer"
    user_id = user.user_id if user else "guest"

    # 1. Process Multipart File Upload
    if file:
        try:
            file_bytes = await file.read()
            if file.filename.lower().endswith(".pdf"):
                try:
                    raw_text = extract_text_from_pdf(file_bytes)
                except ScannedPDFError:
                    images = render_pdf_to_images(file_bytes)
                    if images:
                        extracted = extract_resume_from_images(images, filename=file.filename)
                        raw_text = json.dumps(extracted.dict(), indent=2)
                        parsed_resume = extracted.dict()
            else:
                # Text/DOCX fallback
                raw_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"[AuditRouter] Failed to parse uploaded CV file: {e}")
            raise HTTPException(status_code=400, detail="Could not read uploaded document text.")

    # 2. Process JSON Payload
    if data_json:
        try:
            parsed_body = json.loads(data_json)
            if parsed_body.get("target_role"):
                target_role = parsed_body["target_role"]
            if parsed_body.get("resume_text") and not raw_text:
                raw_text = parsed_body["resume_text"]
            if parsed_body.get("parsed_resume"):
                parsed_resume = parsed_body["parsed_resume"]
                if not raw_text:
                    raw_text = json.dumps(parsed_resume, indent=2)
            if parsed_body.get("user_id") and not user:
                user_id = parsed_body["user_id"]
        except Exception as e:
            logger.warning(f"[AuditRouter] Error parsing data_json form field: {e}")

    # Fallback to direct JSON request body if no multipart file/form
    if not raw_text and not parsed_resume:
        try:
            body = await request.json()
            target_role = body.get("target_role", target_role)
            raw_text = body.get("resume_text", "")
            parsed_resume = body.get("parsed_resume")
            if not raw_text and parsed_resume:
                raw_text = json.dumps(parsed_resume, indent=2)
            if body.get("user_id") and not user:
                user_id = body.get("user_id")
        except Exception:
            pass

    if not raw_text and not parsed_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a resume PDF file or resume text/profile to audit."
        )

    # Run comprehensive audit
    result = await audit_cv_comprehensive(
        raw_text=raw_text,
        target_role=target_role,
        parsed_resume=parsed_resume
    )

    # Check history for prior score delta
    if user_id and user_id in AUDIT_HISTORY_STORE:
        past_cv_audits = [a for a in AUDIT_HISTORY_STORE[user_id] if a.get("audit_type") == "cv"]
        if past_cv_audits:
            last_score = past_cv_audits[-1].get("total_score")
            result.previous_score = last_score
            result.score_delta = result.total_score - last_score

    # Auto-record in memory history
    if user_id:
        if user_id not in AUDIT_HISTORY_STORE:
            AUDIT_HISTORY_STORE[user_id] = []
        AUDIT_HISTORY_STORE[user_id].append({
            "audit_type": "cv",
            "total_score": result.total_score,
            "target_role": target_role
        })

    return result

@router.post("/linkedin", response_model=AuditReportResponse)
async def audit_linkedin_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    data_json: Optional[str] = Form(None),
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """
    Audits a candidate's LinkedIn profile across 27 visibility, writing, and recruiter criteria.
    Accepts either LinkedIn PDF (from 'Save to PDF') or structured profile text.
    """
    profile_text = ""
    target_role = "AI Engineer / Software Engineer"
    user_id = user.user_id if user else "guest"

    # 1. Process Uploaded LinkedIn PDF
    if file:
        try:
            file_bytes = await file.read()
            profile_text = extract_text_from_pdf(file_bytes)
        except Exception as e:
            logger.error(f"[AuditRouter] Failed to parse LinkedIn PDF: {e}")
            raise HTTPException(status_code=400, detail="Could not read LinkedIn PDF. Please ensure it is saved from LinkedIn.")

    # 2. Process Form JSON
    if data_json:
        try:
            parsed = json.loads(data_json)
            if parsed.get("target_role"):
                target_role = parsed["target_role"]
            if parsed.get("profile_text") and not profile_text:
                profile_text = parsed["profile_text"]
            elif not profile_text:
                # Combine structured sections
                parts = []
                if parsed.get("headline"): parts.append(f"Headline: {parsed['headline']}")
                if parsed.get("about"): parts.append(f"About: {parsed['about']}")
                if parsed.get("experience"): parts.append(f"Experience:\n{parsed['experience']}")
                if parsed.get("skills"): parts.append(f"Skills: {parsed['skills']}")
                profile_text = "\n\n".join(parts)
            if parsed.get("user_id") and not user:
                user_id = parsed["user_id"]
        except Exception as e:
            logger.warning(f"[AuditRouter] Error parsing LinkedIn data_json: {e}")

    # Fallback to direct JSON request body
    if not profile_text:
        try:
            body = await request.json()
            target_role = body.get("target_role", target_role)
            if body.get("profile_text"):
                profile_text = body["profile_text"]
            else:
                parts = []
                if body.get("headline"): parts.append(f"Headline: {body['headline']}")
                if body.get("about"): parts.append(f"About: {body['about']}")
                if body.get("experience"): parts.append(f"Experience:\n{body['experience']}")
                if body.get("skills"): parts.append(f"Skills: {body['skills']}")
                profile_text = "\n\n".join(parts)
            if body.get("user_id") and not user:
                user_id = body.get("user_id")
        except Exception:
            pass

    if not profile_text or len(profile_text.strip()) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide LinkedIn profile text or upload your LinkedIn profile PDF."
        )

    # Run LinkedIn audit
    result = await audit_linkedin_comprehensive(
        profile_text=profile_text,
        target_role=target_role
    )

    # History delta
    if user_id and user_id in AUDIT_HISTORY_STORE:
        past_li_audits = [a for a in AUDIT_HISTORY_STORE[user_id] if a.get("audit_type") == "linkedin"]
        if past_li_audits:
            last_score = past_li_audits[-1].get("total_score")
            result.previous_score = last_score
            result.score_delta = result.total_score - last_score

    if user_id:
        if user_id not in AUDIT_HISTORY_STORE:
            AUDIT_HISTORY_STORE[user_id] = []
        AUDIT_HISTORY_STORE[user_id].append({
            "audit_type": "linkedin",
            "total_score": result.total_score,
            "target_role": target_role
        })

    return result

@router.get("/history/{user_id}")
async def get_audit_history(user_id: str):
    """Retrieves past audit records and score progression."""
    history = AUDIT_HISTORY_STORE.get(user_id, [])
    return {"user_id": user_id, "history": history}

@router.post("/save")
async def save_audit_record(payload: AuditSaveRequest):
    """Persists an audit result for tracking."""
    if payload.user_id not in AUDIT_HISTORY_STORE:
        AUDIT_HISTORY_STORE[payload.user_id] = []
    
    AUDIT_HISTORY_STORE[payload.user_id].append(payload.dict())
    return {"status": "success", "message": "Audit record saved."}
