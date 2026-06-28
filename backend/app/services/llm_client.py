import os
import json
import logging
import re
from typing import Type, TypeVar, Optional, List, Dict, Any
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key and not self.api_key.startswith("mock-"):
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY is unset or configured with a mock value. Live API calls will fail.")

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
        system_instruction: Optional[str] = None,
        images: Optional[List[Any]] = None
    ) -> T:
        """
        Call Gemini to generate structured output matching a Pydantic schema.
        Includes a self-correction retry loop that feeds Pydantic validation errors back to the model.
        """
        if not self.client:
            raise ValueError(
                "GEMINI_API_KEY is unset or configured with a mock value. "
                "A valid Gemini API key is required to make live LLM calls."
            )

        model_name = self.get_model_name(model_type)
        
        # Clean up model name: the new SDK expects 'gemini-1.5-flash' or 'gemini-1.5-pro'
        clean_model_name = model_name
        if clean_model_name == "gemini-1.5-flash-latest":
            clean_model_name = "gemini-1.5-flash"
        elif clean_model_name == "gemini-1.5-pro-latest":
            clean_model_name = "gemini-1.5-pro"

        current_prompt = prompt
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            try:
                logger.info(f"Calling Gemini API (Attempt {attempts}/{max_retries}) using {clean_model_name}...")
                
                # Fetch output from Gemini with schema enforcement
                contents = [current_prompt]
                if images:
                    contents.extend(images)

                response = self.client.models.generate_content(
                    model=clean_model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        system_instruction=system_instruction
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
