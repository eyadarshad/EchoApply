import logging
from app.schemas import JDAnalysisResult
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import JD_ANALYSIS_SYSTEM

logger = logging.getLogger(__name__)

async def analyze_job_description(jd_text: str) -> JDAnalysisResult:
    """
    Analyzes a raw job description, extracting structured details.
    Includes explicit instructions to prevent prompt injection from JDs.
    """
    if not jd_text or not jd_text.strip():
        logger.warning("Empty job description received. Returning empty analysis.")
        return JDAnalysisResult(
            role_title="Unknown Role",
            seniority="Mid",
            required_skills=[],
            preferred_skills=[],
            key_responsibilities=[]
        )

    # Clean input to ensure we don't have nested delimiters
    safe_jd_text = jd_text.replace("</job_description_content>", "").replace("<job_description_content>", "")

    prompt = (
        "Analyze the following job description and extract its requirements. "
        "Strictly return structured JSON conforming to the requested schema. If a field is not "
        "clearly specified, return an appropriate generic default or empty list.\n\n"
        "--- START UNTRUSTED JOB DESCRIPTION ---\n"
        "<job_description_content>\n"
        f"{safe_jd_text}\n"
        "</job_description_content>\n"
        "--- END UNTRUSTED JOB DESCRIPTION ---\n"
    )

    logger.info("Executing JD analysis stage...")
    result = await llm_client.generate_structured_async(
        prompt=prompt,
        response_schema=JDAnalysisResult,
        model_type="flash",
        system_instruction=JD_ANALYSIS_SYSTEM
    )
    return result
