import logging
from app.schemas import ResumeParsedData, JDAnalysisResult, GapAnalysisResult
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

def analyze_gaps(profile: ResumeParsedData, jd_analysis: JDAnalysisResult) -> GapAnalysisResult:
    """
    Compares the candidate's profile skills and experience text against
    the job description analysis result. Outputs matched, missing, and partial skills.
    Ensures gaps are reported honestly without fabrication.
    """
    # Quick check for empty requirements
    if not jd_analysis.required_skills and not jd_analysis.preferred_skills:
        logger.warning("No skills specified in JD analysis. Returning empty gap analysis.")
        return GapAnalysisResult(matched_skills=[], missing_skills=[], partial_matches=[])

    system_instruction = (
        "You are an objective ATS parser and gap analyzer. Your goal is to compare the candidate's resume "
        "details (skills list, work experiences, and projects) against the job description requirements "
        "extracted from the target job. You must strictly follow these rules:\n"
        "1. Be completely honest. If a required or preferred skill is NOT mentioned or implied in the "
        "candidate's profile, it MUST be reported in 'missing_skills'. Never hallucinate or pretend the "
        "candidate has a skill they lack.\n"
        "2. Place skills that are present in the candidate's skills list or experience text in 'matched_skills'.\n"
        "3. If a candidate has a related skill but not the exact required one (e.g. they have Flask but the job "
        "requires FastAPI, or they have MySQL but the job requires PostgreSQL), list it in 'partial_matches', "
        "stating the required skill, the candidate's related skill, and the reason."
    )

    prompt = (
        "Perform a gap analysis between the candidate's profile and the job requirements.\n\n"
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
        f"Required Skills: {', '.join(jd_analysis.required_skills)}\n"
        f"Preferred Skills: {', '.join(jd_analysis.preferred_skills)}\n\n"
        "Compare and categorize all required and preferred skills. Return structured JSON conforming to the schema."
    )

    try:
        logger.info("Executing Gap Analysis stage...")
        result = llm_client.generate_structured(
            prompt=prompt,
            response_schema=GapAnalysisResult,
            model_type="flash",
            system_instruction=system_instruction
        )
        return result
    except Exception as e:
        logger.error(f"Error during Gap Analysis stage: {str(e)}")
        # Fallback: categorize all required/preferred skills as missing
        all_skills = list(set(jd_analysis.required_skills + jd_analysis.preferred_skills))
        return GapAnalysisResult(
            matched_skills=[],
            missing_skills=all_skills,
            partial_matches=[]
        )
