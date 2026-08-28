import logging
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.schemas import SaveProfileRequest, SaveProfileResponse, ResumeParsedData
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.services.embedding_service import serialize_profile
from app.services.llm_client import llm_client_resume as llm_client
from app.database import get_db
from app.utils import clean_uuid
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profiles"])

class ProfileResponse(BaseModel):
    user_id: str
    major: str
    location: Optional[str] = None
    parsed_resume: Optional[ResumeParsedData] = None

class ProfileUpdateRequest(BaseModel):
    parsed_resume: ResumeParsedData
    major: Optional[str] = None
    location: Optional[str] = None

@router.post("/profiles", response_model=SaveProfileResponse)
async def save_profile(payload: SaveProfileRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """
    Saves or updates a candidate profile in the database,
    automatically generating and storing its semantic vector embedding.
    """
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to modify this profile"
        )
    user_id = clean_uuid(sanitized_id)
    profile = payload.parsed_resume
    major = sanitize_text_input(payload.major or "Computer Science", max_length=100, field_name="major")
    
    try:
        serialized_text = serialize_profile(profile)
        embedding = llm_client.generate_embedding(serialized_text)
    except Exception as embed_err:
        logger.warning(f"Failed to generate profile embedding: {embed_err}")
        embedding = [0.0] * 768
    
    status_msg = "transient"
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO users (id, email, major)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, major = EXCLUDED.major;
                        """,
                        (user_id, profile.email, major)
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
                        (user_id, json.dumps(profile.model_dump()), embedding)
                    )
                    await conn.commit()
                status_msg = "saved"
    except Exception as db_err:
        logger.warning(f"Failed to save profile {user_id} to DB: {db_err}")
            
    return SaveProfileResponse(
        user_id=user_id,
        status=status_msg
    )

@router.get("/profiles/{user_id}", response_model=ProfileResponse)
@limiter.limit("30/minute")
async def get_profile(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Fetch candidate profile preferences and parsed details from DB."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this profile"
        )
    user_id = clean_uuid(sanitized_id)
    
    major = "Computer Science"
    location = "Karachi"
    parsed_resume = None
    
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT major, location FROM users WHERE id = %s;", (user_id,))
                    row = await cur.fetchone()
                    if row:
                        major = row[0] or "Computer Science"
                        location = row[1] or "Karachi"
                    
                    await cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (user_id,))
                    p_row = await cur.fetchone()
                    if p_row and p_row[0]:
                        parsed_resume = ResumeParsedData.model_validate(p_row[0])
    except Exception as e:
        logger.warning(f"Failed to fetch profile from DB: {e}")
        
    return ProfileResponse(
        user_id=user_id,
        major=major,
        location=parsed_resume.location if parsed_resume and hasattr(parsed_resume, 'location') else location,
        parsed_resume=parsed_resume
    )

@router.patch("/profiles/{user_id}", response_model=SaveProfileResponse)
async def update_profile(user_id: str, payload: ProfileUpdateRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Update custom details of a profile (Phase 4 onboarding and manual corrections)."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to update this profile"
        )
    uid = clean_uuid(sanitized_id)
    profile = payload.parsed_resume
    major = sanitize_text_input(payload.major or "Computer Science", max_length=100, field_name="major") if payload.major else None
    location = sanitize_text_input(payload.location or "", max_length=100, field_name="location") if payload.location else None
    
    try:
        serialized_text = serialize_profile(profile)
        embedding = llm_client.generate_embedding(serialized_text)
    except Exception as embed_err:
        logger.warning(f"Failed to generate profile embedding: {embed_err}")
        embedding = [0.0] * 768
        
    status_msg = "error"
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    if major or location:
                        update_fields = []
                        params = []
                        if major:
                            update_fields.append("major = %s")
                            params.append(major)
                        if location:
                            update_fields.append("location = %s")
                            params.append(location)
                        params.append(uid)
                        await cur.execute(
                            f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s;",
                            tuple(params)
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
                        (uid, json.dumps(profile.model_dump()), embedding)
                    )
                    await conn.commit()
                status_msg = "updated"
    except Exception as db_err:
        logger.warning(f"Failed to patch profile {uid} in DB: {db_err}")
        raise HTTPException(status_code=500, detail="Database write failure.")
        
    return SaveProfileResponse(
        user_id=uid,
        status=status_msg
    )
