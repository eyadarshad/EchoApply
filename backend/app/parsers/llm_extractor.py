import logging
from app.schemas import ResumeParsedData
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

def extract_resume_data(raw_text: str) -> ResumeParsedData:
    """
    Parses unstructured text extracted from a resume PDF and converts it
    into a structured ResumeParsedData model using Gemini 3.5 Flash.
    """
    system_instruction = (
        "You are a professional ATS resume parser. Your goal is to parse raw resume text "
        "and return structured data matching the schema. You must extract names, emails, "
        "contact links, education, experience, skills, and projects accurately. "
        "If a candidate has no work experience (e.g., student or fresher), return an empty list "
        "for experience and focus on education, skills, and projects."
    )

    prompt = (
        "Please analyze the following raw resume text and extract candidate profile details. "
        "Strictly conform to the requested JSON schema. Do not truncate experience or project "
        "descriptions.\n\n"
        f"--- RAW RESUME TEXT ---\n{raw_text}\n"
    )

    try:
        logger.info("Extracting structured resume data via LLM...")
        parsed_data = llm_client.generate_structured(
            prompt=prompt,
            response_schema=ResumeParsedData,
            model_type="flash",
            system_instruction=system_instruction
        )
        return parsed_data
    except Exception as e:
        logger.error(f"Failed to parse resume structured data: {str(e)}")
        raise e
