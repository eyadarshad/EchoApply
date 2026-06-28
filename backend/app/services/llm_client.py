import os
import json
import logging
from typing import Type, TypeVar, Optional
import google.generativeai as genai
from pydantic import BaseModel, ValidationError
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key and not self.api_key.startswith("mock-"):
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY is unset or set to a mock value. Live LLM calls will fail.")

    def get_model_name(self, model_type: str = "flash") -> str:
        """Helper to get current model name configuration."""
        if model_type == "pro":
            return settings.GEMINI_PRO_MODEL or "gemini-1.5-pro-latest"
        return settings.GEMINI_FLASH_MODEL or "gemini-1.5-flash-latest"

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        model_type: str = "flash",
        max_retries: int = 3,
        system_instruction: Optional[str] = None
    ) -> T:
        """
        Call Gemini to generate structured output matching a Pydantic schema.
        Includes a self-correction retry loop that feeds Pydantic validation errors back to the model.
        """
        model_name = self.get_model_name(model_type)
        
        # Set up model configuration
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )

        current_prompt = prompt
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            try:
                logger.info(f"Calling Gemini API (Attempt {attempts}/{max_retries}) using {model_name}...")
                
                # Fetch output from Gemini with schema enforcement
                response = model.generate_content(
                    current_prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                )
                
                text_output = response.text
                if not text_output:
                    raise ValueError("Model returned an empty text response.")

                # Load and validate with Pydantic
                parsed_json = json.loads(text_output)
                validated_model = response_schema.model_validate(parsed_json)
                return validated_model

            except (ValidationError, json.JSONDecodeError, ValueError, Exception) as e:
                error_details = str(e)
                logger.warning(f"Structured output attempt {attempts} failed validation: {error_details}")
                
                if attempts >= max_retries:
                    logger.error("Max retries exceeded for structured LLM call.")
                    raise e
                
                # Append error feedback so the model can self-correct in the next run
                current_prompt = (
                    f"{prompt}\n\n"
                    f"--- CORRECTION REQUEST (Attempt {attempts} failed) ---\n"
                    f"Your previous response failed Pydantic validation with this error:\n"
                    f"{error_details}\n"
                    f"Ensure you return valid JSON conforming to the schema and correct this issue."
                )

# Global client instance
llm_client = LLMClient()
