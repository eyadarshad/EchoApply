import logging
from typing import List, Optional
from app.schemas import ResumeParsedData

logger = logging.getLogger(__name__)

def serialize_profile(profile: ResumeParsedData) -> str:
    """
    Serializes candidate profile into standard text representation for semantic embedding.
    """
    parts = []
    
    # 1. Basic details
    if hasattr(profile, 'name') and profile.name:
        parts.append(f"Candidate Name: {profile.name}")
    
    # 2. Skills
    if hasattr(profile, 'skills') and profile.skills:
        parts.append(f"Skills: {', '.join(profile.skills)}")
        
    # 3. Experience
    if hasattr(profile, 'experience') and profile.experience:
        parts.append("Work Experience:")
        for exp in profile.experience:
            role = getattr(exp, 'role', '') or exp.get('role', '') if isinstance(exp, dict) else getattr(exp, 'role', '')
            company = getattr(exp, 'company', '') or exp.get('company', '') if isinstance(exp, dict) else getattr(exp, 'company', '')
            bullets = getattr(exp, 'bullets', []) or exp.get('bullets', []) if isinstance(exp, dict) else getattr(exp, 'bullets', [])
            
            exp_str = f"- Role: {role} at {company}."
            if bullets:
                exp_str += f" Achievements: {' '.join(bullets)}"
            parts.append(exp_str)
            
    # 4. Projects
    if hasattr(profile, 'projects') and profile.projects:
        parts.append("Projects:")
        for proj in profile.projects:
            name = getattr(proj, 'name', '') or proj.get('name', '') if isinstance(proj, dict) else getattr(proj, 'name', '')
            bullets = getattr(proj, 'bullets', []) or proj.get('bullets', []) if isinstance(proj, dict) else getattr(proj, 'bullets', [])
            
            proj_str = f"- Project Name: {name}."
            if bullets:
                proj_str += f" Description: {' '.join(bullets)}"
            parts.append(proj_str)

    return "\n".join(parts)

def serialize_job(title: str, company: str, jd_text: str) -> str:
    """
    Serializes job details into standard text representation for semantic embedding.
    """
    return f"Job Title: {title}\nCompany: {company}\nJob Description:\n{jd_text}"

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculates cosine similarity between two 768-dimensional float lists.
    Serves as the database-offline in-memory fallback.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = sum(a * a for a in v1) ** 0.5
    magnitude_v2 = sum(a * a for a in v2) ** 0.5
    
    if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
        return 0.0
        
    return dot_product / (magnitude_v1 * magnitude_v2)
