import logging
from typing import Dict, Any, Optional

from app.schemas import (
    ResumeParsedData, ResumeTailorRequest, ResumeTailorResponse,
    GapAnalysisResult, TruthfulnessCheckResult
)
from app.pipeline.stages.jd_analysis import analyze_job_description
from app.pipeline.stages.technique_selection import select_techniques
from app.pipeline.stages.gap_analysis import analyze_gaps
from app.pipeline.stages.rewrite import rewrite_bullets
from app.pipeline.stages.impact import run_impact_pass
from app.pipeline.stages.truthfulness import verify_truthfulness

logger = logging.getLogger(__name__)

def tailor_resume_flow(profile: ResumeParsedData, jd_text: str, major: str = "Computer Science") -> Dict[str, Any]:
    """
    Sequences the 7-stage tailoring pipeline:
    1. JD Analysis
    2. Technique Selection
    3. Gap Analysis
    4. Targeted Rewrite
    5. Impact Pass & Density Control (Trimming)
    6. Truthfulness Gate
    7. Compile final structured profile
    """
    logger.info("Starting tailoring flow...")

    # Stage 1: JD Analysis
    jd_analysis = analyze_job_description(jd_text)

    # Stage 2: Technique Selection
    techniques = select_techniques(major)

    # Stage 3: Gap Analysis
    gap_analysis = analyze_gaps(profile, jd_analysis)

    # Stage 4: Targeted Rewrite
    rewrite_result = rewrite_bullets(profile, gap_analysis)

    # Stage 5: Impact Pass & Trimming
    impact_result = run_impact_pass(profile, jd_analysis, rewrite_result, techniques)

    # Stage 6: Truthfulness Gate
    truthfulness_report = verify_truthfulness(profile, impact_result)

    # Calculate basic ATS score based on keyword match percentage
    total_jd_skills = len(gap_analysis.matched_skills) + len(gap_analysis.missing_skills)
    if total_jd_skills > 0:
        ats_score = int((len(gap_analysis.matched_skills) / total_jd_skills) * 100)
    else:
        ats_score = 80  # Default fallback if no skills in JD

    # Compile the final tailored profile content JSON
    # This structure can be directly fed into the PDF/Word renderers
    highlights_data = [
        {"skill": h.skill, "relevance_reason": h.relevance_reason}
        for h in impact_result.highlights_strip
    ]

    content_json = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "links": profile.links,
        "skills": profile.skills,  # Keep original skills list, Highlights Strip highlights the top ones
        "education": [edu for edu in profile.education],
        "experience": impact_result.tailored_experience,
        "projects": [proj for proj in profile.projects],  # Projects could be trimmed or tailored in future phases
        "anchor_line": impact_result.anchor_line,
        "highlights_strip": highlights_data
    }

    return {
        "content_json": content_json,
        "gap_analysis": gap_analysis,
        "truthfulness_report": truthfulness_report,
        "ats_score": ats_score
    }
