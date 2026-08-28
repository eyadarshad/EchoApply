import logging
from app.schemas import ResumeParsedData, JDAnalysisResult, GapAnalysisResult
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import GAP_ANALYSIS_SYSTEM

logger = logging.getLogger(__name__)

async def analyze_gaps(profile: ResumeParsedData, jd_analysis: JDAnalysisResult) -> GapAnalysisResult:
    """
    Compares the candidate's profile skills and experience text against
    the job description analysis result. Outputs matched, missing, and partial skills.
    Ensures gaps are reported honestly without fabrication.
    """
    # Quick check for empty requirements
    if not jd_analysis.required_skills and not jd_analysis.preferred_skills:
        logger.warning("No skills specified in JD analysis. Returning empty gap analysis.")
        return GapAnalysisResult(matched_skills=[], missing_skills=[], partial_matches=[])

    prompt = (
        "Act as a senior recruiter for this exact company. Analyze my resume against this job description and give me "
        "a matching score out of the 100, the top five missing keywords, and the three red flags a hiring manager would spot under a few seconds.\n\n"
        "--- CANDIDATE PROFILE DETAILS ---\n"
        f"Skills list: {', '.join(profile.skills)}\n"
        "Experiences:\n"
    )
    for exp in profile.experience:
        bullets = "; ".join(exp.get("bullets", []))
        prompt += f"- Role: {exp.get('role', '')} at {exp.get('company', '')}: {bullets}\n"
    
    prompt += "Projects:\n"
    for proj in profile.projects:
        bullets = "; ".join(proj.get("bullets", []))
        prompt += f"- Project: {proj.get('name', '')}: {bullets}\n\n"

    prompt += (
        "--- JOB DESCRIPTION REQUIREMENTS ---\n"
        f"Role Title: {jd_analysis.role_title}\n"
        f"Required Skills: {', '.join(jd_analysis.required_skills)}\n"
        f"Preferred Skills: {', '.join(jd_analysis.preferred_skills)}\n\n"
        "Compare and categorize all required and preferred skills. Extract exactly the top 5 missing keywords, "
        "exactly the top 3 red flags, and the overall matching score. Return structured JSON conforming to the schema."
    )

    try:
        logger.info("Executing Gap Analysis stage...")
        result = await llm_client.generate_structured_async(
            prompt=prompt,
            response_schema=GapAnalysisResult,
            model_type="flash",
            system_instruction=GAP_ANALYSIS_SYSTEM
        )
        return result
    except Exception as e:
        logger.error(f"Error during Gap Analysis stage: {str(e)}")
        # Fallback: categorize all required/preferred skills as missing
        all_skills = list(set(jd_analysis.required_skills + jd_analysis.preferred_skills))
        return GapAnalysisResult(
            matched_skills=[],
            missing_skills=all_skills,
            partial_matches=[],
            missing_keywords=[],
            red_flags=["Error performing gap analysis; defaulting to fallback red flags."]
        )
