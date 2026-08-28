import logging
from app.schemas import ResumeParsedData
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import RESUME_EXTRACTION_SYSTEM, RESUME_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

def extract_resume_data(raw_text: str) -> ResumeParsedData:
    """
    Parses unstructured text extracted from a resume PDF and converts it
    into a structured ResumeParsedData model using Gemini 3.5 Flash.
    """
    prompt = RESUME_EXTRACTION_PROMPT.format(raw_text=raw_text)

    try:
        logger.info("Extracting structured resume data via LLM...")
        logger.debug(f"[DEBUG Prompt] Exact full prompt + document text sent to Gemini:\n{prompt}")
        parsed_data = llm_client.generate_structured(
            prompt=prompt,
            response_schema=ResumeParsedData,
            model_type="flash",
            system_instruction=RESUME_EXTRACTION_SYSTEM
        )
        return parsed_data
    except Exception as e:
        logger.error(f"Failed to parse resume structured data: {str(e)}")
        raise e

def extract_resume_from_images(images: list, filename: str = "") -> ResumeParsedData:
    """
    Directly extracts structured resume data from rendered page images
    using Gemini's multimodal (Vision) capabilities.
    """
    prompt = (
        "Please carefully read all pages of this resume and extract candidate profile details. "
        "Strictly conform to the requested JSON schema. If details like experience or projects are "
        "not present, leave those arrays empty."
    )
    if filename:
        prompt += f"\nNote: Source filename is '{filename}'."
    
    try:
        logger.info("Extracting structured resume data via Gemini Vision multimodal call...")
        logger.debug(f"[DEBUG Prompt] Exact full prompt + document text sent to Gemini (multimodal):\n{prompt}")
        parsed_data = llm_client.generate_structured(
            prompt=prompt,
            response_schema=ResumeParsedData,
            model_type="flash",
            system_instruction=RESUME_EXTRACTION_SYSTEM,
            images=images
        )
        return parsed_data
    except Exception as e:
        logger.error(f"Multimodal parsing failed: {str(e)}")
        raise e
