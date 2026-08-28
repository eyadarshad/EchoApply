import os
import json
import logging
import re
import time
import httpx
from typing import Type, TypeVar, Optional, List, Dict, Any, Tuple
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from app.config import settings
from app.services.metrics import metrics_service

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class GeminiKeyPool:
    def __init__(self, purpose: str, keys: List[str]):
        self.purpose = purpose
        # deduplicate and filter
        seen = set()
        self.keys = []
        for k in keys:
            if k and not k.startswith("mock-") and k not in seen:
                seen.add(k)
                self.keys.append(k)
        
        self.cool_downs = {k: 0.0 for k in self.keys}
        self.current_index = 0
        self.is_rate_limited = {k: False for k in self.keys}
        logger.info(f"GeminiKeyPool ({purpose}): Initialized with {len(self.keys)} unique keys.")

    def get_key(self) -> Optional[str]:
        if not self.keys:
            return None
        
        now = time.time()
        for i in range(len(self.keys)):
            idx = (self.current_index + i) % len(self.keys)
            key = self.keys[idx]
            if now >= self.cool_downs[key]:
                self.current_index = idx
                return key
        
        # If all keys cooled down, find the one that recovers first
        min_cooldown = min(self.cool_downs.values())
        for key, cd_time in self.cool_downs.items():
            if cd_time == min_cooldown:
                return key
        return self.keys[0]

    def report_failure(self, key: str, status_code: int = 429):
        if key in self.keys:
            if status_code == 429:
                self.cool_downs[key] = time.time() + 60.0
                self.is_rate_limited[key] = True
                logger.warning(f"GeminiKeyPool ({self.purpose}): Key ...{key[-6:]} got 429 (Rate Limit). Cooldown 60s.")
            else:
                self.cool_downs[key] = time.time() + 10.0
                logger.warning(f"GeminiKeyPool ({self.purpose}): Key ...{key[-6:]} failed with code {status_code}. Cooldown 10s.")
            self.current_index = (self.current_index + 1) % len(self.keys)

    def report_success(self, key: str):
        if key in self.keys:
            self.cool_downs[key] = 0.0
            self.is_rate_limited[key] = False


class LLMClient:
    def __init__(self, purpose: str, keys: List[str]):
        self.purpose = purpose
        self.key_pool = GeminiKeyPool(purpose, keys)
        self.clients = {}
        self.fallback_occurred = False
        
        import sys
        is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "true"
        
        if is_testing:
            logger.info(f"LLMClient ({purpose}): Testing mode active. Fallbacks forced.")
            self.key_pool.keys = []
            
        # Initialize clients for valid keys
        for key in self.key_pool.keys:
            self.clients[key] = genai.Client(api_key=key)

    def _get_client(self) -> Tuple[Optional[str], Optional[genai.Client]]:
        key = self.key_pool.get_key()
        if not key:
            return None, None
        return key, self.clients.get(key)

    def _call_groq_structured(self, prompt: str, response_schema: Type[T], system_instruction: str = "") -> Optional[T]:
        """Call Groq API for structured JSON output — fast fallback before OpenRouter."""
        groq_key = settings.GROQ_API_KEY
        if not groq_key:
            return None
        
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("groq_api", failure_threshold=5, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("Groq circuit breaker is OPEN. Skipping.")
            return None
        
        schema_json = response_schema.model_json_schema()
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": f"{prompt}\n\nReturn ONLY valid JSON conforming to this schema:\n{json.dumps(schema_json, indent=2)}"})
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                        "max_tokens": 4096
                    }
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                if content.strip().startswith("```"):
                    lines = content.strip().split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                parsed = json.loads(content)
                validated = response_schema.model_validate(parsed)
                logger.info("Groq (llama-3.3-70b-versatile) structured call succeeded.")
                metrics_service.record_llm_call("groq-llama-3.3-70b", 0.001)
                breaker.record_success()
                return validated
        except Exception as e:
            metrics_service.record_llm_failure()
            breaker.record_failure()
            logger.warning(f"Groq structured call failed: {e}")
            return None

    def _call_groq_text(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        """Call Groq API for plain text output — fast fallback before OpenRouter."""
        groq_key = settings.GROQ_API_KEY
        if not groq_key:
            return None
        
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("groq_api", failure_threshold=5, recovery_timeout=60.0)
        if not breaker.allow_request():
            return None
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                logger.info("Groq (llama-3.3-70b-versatile) text call succeeded.")
                metrics_service.record_llm_call("groq-llama-3.3-70b", 0.0005)
                breaker.record_success()
                return content
        except Exception as e:
            metrics_service.record_llm_failure()
            breaker.record_failure()
            logger.warning(f"Groq text call failed: {e}")
            return None

    def _call_openrouter_structured_single(self, prompt: str, response_schema: Type[T], system_instruction: str, model: str) -> Optional[T]:
        """Call OpenRouter API for structured JSON output on a specific model."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("openrouter_api", failure_threshold=5, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("OpenRouter circuit breaker is OPEN. Skipping request.")
            return None

        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            return None
        
        schema_json = response_schema.model_json_schema()
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": f"{prompt}\n\nReturn ONLY valid JSON conforming to this schema:\n{json.dumps(schema_json, indent=2)}"})
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://echoapply.ai",
                        "X-Title": "Echo Apply"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                        "max_tokens": 4096
                    }
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                if content.strip().startswith("```"):
                    lines = content.strip().split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                parsed = json.loads(content)
                validated = response_schema.model_validate(parsed)
                logger.info(f"OpenRouter ({model}) structured call succeeded.")
                metrics_service.record_llm_call(model, 0.002)
                breaker.record_success()
                return validated
        except Exception as e:
            metrics_service.record_llm_failure()
            breaker.record_failure()
            logger.warning(f"OpenRouter ({model}) structured call failed: {e}")
            return None

    def _call_openrouter_structured(self, prompt: str, response_schema: Type[T], system_instruction: str = "", model_override: str = "") -> Optional[T]:
        """Structured OpenRouter call with automatic chain fallback."""
        models_to_try = [model_override] if model_override else [
            settings.OPENROUTER_MODEL_PRIMARY or "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            "nvidia/llama-3.1-nemotron-3.5-lightning:free",
            settings.OPENROUTER_MODEL_SECONDARY or "nvidia/llama-3.3-nemotron-super-49b-v1:free",
            settings.OPENROUTER_MODEL_TERTIARY or "meta-llama/llama-3.3-70b-instruct:free"
        ]
        
        for model in models_to_try:
            if not model:
                continue
            res = self._call_openrouter_structured_single(prompt, response_schema, system_instruction, model)
            if res:
                return res
        return None

    def _call_openrouter_text_single(self, prompt: str, system_instruction: str, model: str) -> Optional[str]:
        """Call OpenRouter API for plain text output on a specific model."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("openrouter_api", failure_threshold=5, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("OpenRouter circuit breaker is OPEN. Skipping request.")
            return None

        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            return None
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://echoapply.ai",
                        "X-Title": "Echo Apply"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                logger.info(f"OpenRouter ({model}) text call succeeded.")
                metrics_service.record_llm_call(model, 0.001)
                breaker.record_success()
                return content
        except Exception as e:
            metrics_service.record_llm_failure()
            breaker.record_failure()
            logger.warning(f"OpenRouter ({model}) text call failed: {e}")
            return None

    def _call_openrouter_text(self, prompt: str, system_instruction: str = "", model_override: str = "") -> Optional[str]:
        """Plain text OpenRouter call with automatic chain fallback."""
        models_to_try = [model_override] if model_override else [
            settings.OPENROUTER_MODEL_PRIMARY or "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            "nvidia/llama-3.1-nemotron-3.5-lightning:free",
            settings.OPENROUTER_MODEL_SECONDARY or "nvidia/llama-3.3-nemotron-super-49b-v1:free",
            settings.OPENROUTER_MODEL_TERTIARY or "meta-llama/llama-3.3-70b-instruct:free"
        ]
        
        for model in models_to_try:
            if not model:
                continue
            res = self._call_openrouter_text_single(prompt, system_instruction, model)
            if res:
                return res
        return None

    def get_model_name(self, model_type: str = "flash") -> str:
        """Helper to get current model name configuration."""
        if model_type == "pro":
            return settings.GEMINI_PRO_MODEL or "gemini-2.5-pro"
        return settings.GEMINI_FLASH_MODEL or "gemini-2.5-flash"

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
        Includes rotation-based retrying and correction feedback.
        """
        from app.services.llm_prompts import MASTER_SYSTEM_PREFIX
        full_system_instruction = MASTER_SYSTEM_PREFIX
        if system_instruction:
            full_system_instruction += "\n" + system_instruction

        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("gemini_api", failure_threshold=5, recovery_timeout=60.0)

        # Fallback helper: Gemini exhausted → try Groq → then OpenRouter → then heuristic
        def run_structured_fallback() -> T:
            groq_result = self._call_groq_structured(prompt, response_schema, full_system_instruction)
            if groq_result:
                return groq_result
            or_result = self._call_openrouter_structured(prompt, response_schema, full_system_instruction)
            if or_result:
                return or_result
            from app.services.heuristic_parser import handle_heuristic_fallback
            return handle_heuristic_fallback(prompt, response_schema)

        clean_model_name = self.get_model_name(model_type)
        current_prompt = prompt
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            key, client = self._get_client()
            
            if not client or not breaker.allow_request():
                if not client:
                    logger.info(f"LLMClient ({self.purpose}): No Gemini client available. Using fallbacks.")
                else:
                    logger.warning(f"LLMClient ({self.purpose}): Gemini breaker is OPEN. Using fallbacks.")
                return run_structured_fallback()

            try:
                logger.info(f"LLMClient ({self.purpose}): Calling Gemini API (Key ...{key[-6:]}) using {clean_model_name}...")
                
                contents = [current_prompt]
                if images:
                    contents.extend(images)

                response = client.models.generate_content(
                    model=clean_model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        system_instruction=full_system_instruction
                    )
                )
                
                text_output = response.text
                if not text_output:
                    raise ValueError("Model returned an empty text response.")

                parsed_json = json.loads(text_output)
                validated_model = response_schema.model_validate(parsed_json)
                
                if key:
                    self.key_pool.report_success(key)
                
                metrics_service.record_llm_call(clean_model_name, 0.0001 if model_type == "flash" else 0.005)
                breaker.record_success()
                return validated_model

            except Exception as e:
                metrics_service.record_llm_failure()
                error_details = str(e)
                logger.warning(f"LLMClient ({self.purpose}): Attempt {attempts} failed structured validation: {error_details}")
                
                # Check for rate limits or connection errors to rotate/cooldown keys
                is_rate_limit = "429" in error_details or "RESOURCE_EXHAUSTED" in error_details
                if key:
                    self.key_pool.report_failure(key, 429 if is_rate_limit else 500)
                
                if not isinstance(e, (ValidationError, json.JSONDecodeError, ValueError)):
                    breaker.record_failure()
                
                if attempts >= max_retries:
                    if model_type == "pro":
                        logger.warning(f"LLMClient ({self.purpose}): Pro call failed. Retrying with Flash model...")
                        return self.generate_structured(
                            prompt=prompt,
                            response_schema=response_schema,
                            model_type="flash",
                            max_retries=2,
                            system_instruction=system_instruction,
                            images=images
                        )
                    logger.warning(f"LLMClient ({self.purpose}): Gemini structured call exhausted. Fallback to OpenRouter chain...")
                    return run_structured_fallback()
                
                current_prompt = (
                    f"{prompt}\n\n"
                    f"--- CORRECTION REQUEST (Attempt {attempts} failed) ---\n"
                    f"Your previous response failed validation with this error:\n"
                    f"{error_details}\n"
                    f"Ensure you return valid JSON conforming to the schema and correct this issue."
                )

        return run_structured_fallback()

    async def generate_structured_async(
        self,
        prompt: str,
        response_schema: Type[T],
        model_type: str = "flash",
        max_retries: int = 3,
        system_instruction: Optional[str] = None,
        images: Optional[List[Any]] = None
    ) -> T:
        """Asynchronously call Gemini with rotation-based retrying."""
        from app.services.llm_prompts import MASTER_SYSTEM_PREFIX
        full_system_instruction = MASTER_SYSTEM_PREFIX
        if system_instruction:
            full_system_instruction += "\n" + system_instruction

        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("gemini_api", failure_threshold=5, recovery_timeout=60.0)

        # Fallback helper: Gemini exhausted → try Groq → then OpenRouter → then heuristic
        async def run_structured_async_fallback() -> T:
            import asyncio
            groq_result = await asyncio.to_thread(
                self._call_groq_structured,
                prompt,
                response_schema,
                full_system_instruction
            )
            if groq_result:
                return groq_result
            or_result = await asyncio.to_thread(
                self._call_openrouter_structured,
                prompt,
                response_schema,
                full_system_instruction
            )
            if or_result:
                return or_result
            from app.services.heuristic_parser import handle_heuristic_fallback
            return handle_heuristic_fallback(prompt, response_schema)

        clean_model_name = self.get_model_name(model_type)
        current_prompt = prompt
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            key, client = self._get_client()
            
            if not client or not breaker.allow_request():
                if not client:
                    logger.info(f"LLMClient ({self.purpose}) [Async]: No Gemini client available. Using fallbacks.")
                else:
                    logger.warning(f"LLMClient ({self.purpose}) [Async]: Gemini breaker is OPEN. Using fallbacks.")
                return await run_structured_async_fallback()

            try:
                logger.info(f"LLMClient ({self.purpose}) [Async]: Calling Gemini (Key ...{key[-6:]}) using {clean_model_name}...")
                
                contents = [current_prompt]
                if images:
                    contents.extend(images)

                response = await client.aio.models.generate_content(
                    model=clean_model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        system_instruction=full_system_instruction
                    )
                )
                
                text_output = response.text
                if not text_output:
                    raise ValueError("Model returned an empty text response.")

                parsed_json = json.loads(text_output)
                validated_model = response_schema.model_validate(parsed_json)
                
                if key:
                    self.key_pool.report_success(key)
                
                breaker.record_success()
                return validated_model

            except Exception as e:
                error_details = str(e)
                logger.warning(f"LLMClient ({self.purpose}) [Async]: Attempt {attempts} failed structured validation: {error_details}")
                
                is_rate_limit = "429" in error_details or "RESOURCE_EXHAUSTED" in error_details
                if key:
                    self.key_pool.report_failure(key, 429 if is_rate_limit else 500)
                
                if not isinstance(e, (ValidationError, json.JSONDecodeError, ValueError)):
                    breaker.record_failure()
                
                if attempts >= max_retries:
                    if model_type == "pro":
                        logger.warning(f"LLMClient ({self.purpose}) [Async]: Pro call failed. Retrying with Flash model...")
                        return await self.generate_structured_async(
                            prompt=prompt,
                            response_schema=response_schema,
                            model_type="flash",
                            max_retries=2,
                            system_instruction=system_instruction,
                            images=images
                        )
                    logger.warning(f"LLMClient ({self.purpose}) [Async]: Gemini structured call exhausted. Fallback to OpenRouter chain...")
                    return await run_structured_async_fallback()
                
                current_prompt = (
                    f"{prompt}\n\n"
                    f"--- CORRECTION REQUEST (Attempt {attempts} failed) ---\n"
                    f"Your previous response failed validation with this error:\n"
                    f"{error_details}\n"
                    f"Ensure you return valid JSON conforming to the schema and correct this issue."
                )

        return await run_structured_async_fallback()

    def generate_text(
        self,
        prompt: str,
        model_type: str = "flash",
        system_instruction: Optional[str] = None
    ) -> str:
        """Call Gemini to generate plain text output."""
        from app.services.llm_prompts import MASTER_SYSTEM_PREFIX
        full_system_instruction = MASTER_SYSTEM_PREFIX
        if system_instruction:
            full_system_instruction += "\n" + system_instruction

        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("gemini_api", failure_threshold=5, recovery_timeout=60.0)

        def run_text_fallback() -> str:
            groq_text = self._call_groq_text(prompt, full_system_instruction)
            if groq_text:
                return groq_text
            or_text = self._call_openrouter_text(prompt, full_system_instruction)
            return or_text or ""

        clean_model_name = self.get_model_name(model_type)
        attempts = 0
        max_retries = 2

        while attempts < max_retries:
            attempts += 1
            key, client = self._get_client()
            
            if not client or not breaker.allow_request():
                if not client:
                    logger.info(f"LLMClient ({self.purpose}): No Gemini keys configured. Using text fallbacks.")
                else:
                    logger.warning(f"LLMClient ({self.purpose}): Gemini breaker is OPEN. Using text fallbacks.")
                return run_text_fallback()
            
            try:
                response = client.models.generate_content(
                    model=clean_model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=full_system_instruction
                    )
                )
                if key:
                    self.key_pool.report_success(key)
                breaker.record_success()
                return response.text or ""
            except Exception as e:
                error_details = str(e)
                is_rate_limit = "429" in error_details or "RESOURCE_EXHAUSTED" in error_details
                if key:
                    self.key_pool.report_failure(key, 429 if is_rate_limit else 500)
                breaker.record_failure()
                logger.warning(f"LLMClient ({self.purpose}): Gemini generate_text failed: {e}.")
                if attempts >= max_retries:
                    logger.warning(f"LLMClient ({self.purpose}): Fallback to OpenRouter text fallback chain.")
                    return run_text_fallback()

        return run_text_fallback()

    async def generate_text_async(
        self,
        prompt: str,
        model_type: str = "flash",
        system_instruction: Optional[str] = None
    ) -> str:
        """Call Gemini asynchronously to generate plain text output."""
        import asyncio
        return await asyncio.to_thread(self.generate_text, prompt, model_type, system_instruction)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate 768-dimensional vector embedding for a given text.
        Gracefully falls back to a deterministic dummy vector on API rate limits or failures.
        """
        if not text:
            return [0.0] * 768

        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("gemini_embedding_api", failure_threshold=5, recovery_timeout=60.0)

        def run_dummy_embedding() -> List[float]:
            import hashlib
            h = hashlib.sha256(text.encode('utf-8')).digest()
            dummy = []
            for i in range(768):
                idx = i % len(h)
                dummy.append(float(h[idx]) / 127.5 - 1.0)
            return dummy

        key, client = self._get_client()
        if not client or self.fallback_occurred or not breaker.allow_request():
            return run_dummy_embedding()

        try:
            response = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=768
                )
            )
            if response and response.embeddings:
                breaker.record_success()
                if key:
                    self.key_pool.report_success(key)
                return response.embeddings[0].values
            raise ValueError("No embeddings returned by Gemini.")
        except Exception as e:
            error_details = str(e)
            is_rate_limit = "429" in error_details or "RESOURCE_EXHAUSTED" in error_details
            if key:
                self.key_pool.report_failure(key, 429 if is_rate_limit else 500)
            breaker.record_failure()
            logger.error(f"!!! DUMMY EMBEDDING FALLBACK TRIGGERED (API Exception): {e} !!!")
            return run_dummy_embedding()

    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Concurrently generate embeddings for a batch of texts using the async client."""
        key, client = self._get_client()
        if not client or self.fallback_occurred:
            return [self.generate_embedding(t) for t in texts]

        import asyncio
        sem = asyncio.Semaphore(5)

        async def _embed_single(text: str) -> List[float]:
            if not text:
                return [0.0] * 768
            async with sem:
                try:
                    response = await client.aio.models.embed_content(
                        model="gemini-embedding-2",
                        contents=text,
                        config=types.EmbedContentConfig(
                            output_dimensionality=768
                        )
                    )
                    if response and response.embeddings:
                        return response.embeddings[0].values
                    raise ValueError("Empty embedding response.")
                except Exception as e:
                    error_details = str(e)
                    is_rate_limit = "429" in error_details or "RESOURCE_EXHAUSTED" in error_details
                    if key:
                        self.key_pool.report_failure(key, 429 if is_rate_limit else 500)
                    logger.error(f"!!! ASYNC DUMMY EMBEDDING FALLBACK TRIGGERED: {e} !!!")
                    import hashlib
                    h = hashlib.sha256(text.encode('utf-8')).digest()
                    dummy = []
                    for i in range(768):
                        idx = i % len(h)
                        dummy.append(float(h[idx]) / 127.5 - 1.0)
                    return dummy

        tasks = [_embed_single(t) for t in texts]
        return await asyncio.gather(*tasks)


# Instantiate purpose-specific clients
llm_client_resume = LLMClient(purpose="resume", keys=[settings.GEMINI_API_KEY_RESUME])
llm_client_search = LLMClient(purpose="search", keys=[settings.GEMINI_API_KEY_SEARCH])
llm_client_general = LLMClient(purpose="general", keys=[settings.GEMINI_API_KEY_GENERAL])

# Global legacy client instance pooling all available keys for backward compatibility
llm_client = LLMClient(
    purpose="legacy", 
    keys=[
        settings.GEMINI_API_KEY_GENERAL,
        settings.GEMINI_API_KEY_RESUME,
        settings.GEMINI_API_KEY_SEARCH,
        settings.GEMINI_API_KEY
    ]
)
