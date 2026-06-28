import os
import json
import logging
import re
from typing import Type, TypeVar, Optional, List, Dict, Any
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
            logger.warning("GEMINI_API_KEY is unset or set to a mock value. Live LLM calls will fail. Entering simulation mode.")

    def get_model_name(self, model_type: str = "flash") -> str:
        """Helper to get current model name configuration."""
        if model_type == "pro":
            return settings.GEMINI_PRO_MODEL or "gemini-1.5-pro-latest"
        return settings.GEMINI_FLASH_MODEL or "gemini-1.5-flash-latest"

    def _generate_mock_response(self, prompt: str, response_schema: Type[T]) -> T:
        """
        Generates structured, high-fidelity mock responses based on prompt keywords
        to simulate live Gemini calls when the API key is unavailable.
        """
        schema_name = response_schema.__name__
        text_lower = prompt.lower()

        if schema_name == "JDAnalysisResult":
            # Extract required and preferred skills from the raw JD in prompt
            required = []
            preferred = []
            
            if "python" in text_lower:
                required.append("Python")
            if "fastapi" in text_lower:
                required.append("FastAPI")
            if "postgresql" in text_lower or "postgres" in text_lower:
                required.append("PostgreSQL")
            if "kubernetes" in text_lower or "k8s" in text_lower:
                preferred.append("Kubernetes")
            if "docker" in text_lower:
                preferred.append("Docker")
            if "react" in text_lower:
                required.append("React")
            if "typescript" in text_lower:
                required.append("TypeScript")
            if "java" in text_lower:
                required.append("Java")
            if "spring boot" in text_lower:
                required.append("Spring Boot")
            if "aws" in text_lower:
                required.append("AWS")
            if "mysql" in text_lower:
                required.append("MySQL")
            if "terraform" in text_lower:
                preferred.append("Terraform")

            if not required:
                required = ["Python", "FastAPI"]
            if not preferred:
                preferred = ["Docker"]

            role_title = "Software Engineer"
            if "backend" in text_lower:
                role_title = "Backend Engineer"
            elif "frontend" in text_lower:
                role_title = "Frontend Developer"

            seniority = "Junior"
            if "senior" in text_lower:
                seniority = "Senior"
            elif "intern" in text_lower:
                seniority = "Intern"

            return response_schema(
                role_title=role_title,
                seniority=seniority,
                required_skills=required,
                preferred_skills=preferred,
                key_responsibilities=["Develop and optimize backend APIs.", "Collaborate on database query performance."]
            )

        elif schema_name == "GapAnalysisResult":
            # Parse candidate skills list from prompt
            candidate_skills = []
            skills_match = re.search(r"Skills list: ([^\n]+)", prompt)
            if skills_match:
                candidate_skills = [s.strip().lower() for s in skills_match.group(1).split(",")]

            # Parse required/preferred skills
            req_match = re.search(r"Required Skills: ([^\n]*)", prompt)
            pref_match = re.search(r"Preferred Skills: ([^\n]*)", prompt)
            
            req_skills = [s.strip() for s in req_match.group(1).split(",")] if req_match and req_match.group(1) else []
            pref_skills = [s.strip() for s in pref_match.group(1).split(",")] if pref_match and pref_match.group(1) else []
            
            all_target_skills = list(set([s for s in req_skills + pref_skills if s.strip()]))
            if not all_target_skills:
                all_target_skills = ["Python", "FastAPI", "PostgreSQL", "Kubernetes"]

            matched = []
            missing = []
            partial = []

            for s in all_target_skills:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if s_clean.lower() in candidate_skills:
                    matched.append(s_clean)
                else:
                    if s_clean.lower() == "kubernetes" and "docker" in candidate_skills:
                        partial.append({
                            "jd_skill": "Kubernetes",
                            "user_skill": "Docker",
                            "reason": "Candidate has containerization experience but lacks specific Kubernetes orchestration."
                        })
                    else:
                        missing.append(s_clean)

            return response_schema(
                matched_skills=matched,
                missing_skills=missing,
                partial_matches=partial
            )

        elif schema_name == "TargetedRewriteResult":
            # Parse bullets list from prompt (prefixed by numbers)
            bullets = re.findall(r"\d+\.\s+([^\n]+)", prompt)
            if not bullets:
                bullets = [
                    "Developed backend services using Python and FastAPI.",
                    "Optimized database queries decreasing latency by 20%."
                ]

            rewritten_bullets = []
            for b in bullets:
                rewritten = b
                b_clean = b.strip()
                if "Developed backend services" in b_clean:
                    rewritten = "Engineered production-grade REST APIs and backend microservices using Python and FastAPI."
                elif "Optimized database queries" in b_clean:
                    rewritten = "Optimized PostgreSQL queries decreasing search latency by 20% under high load."
                elif "Built web interfaces" in b_clean:
                    rewritten = "Designed responsive frontend interfaces utilizing React and Tailwind CSS."
                elif "Improved site responsiveness" in b_clean:
                    rewritten = "Optimized viewport responsive layouts improving mobile browser compatibility."

                rewritten_bullets.append({
                    "original_bullet": b_clean,
                    "rewritten_bullet": rewritten
                })

            return response_schema(rewritten_bullets=rewritten_bullets)

        elif schema_name == "ImpactPassResult":
            anchor_line = "Performance-driven Software Engineer specializing in FastAPI backend design and PostgreSQL database optimization."
            
            highlights_strip = [
                {
                    "skill": "FastAPI APIs",
                    "relevance_reason": "Candidate has hands-on backend Intern experience building FastAPI REST services."
                },
                {
                    "skill": "PostgreSQL Tuning",
                    "relevance_reason": "Candidate optimized queries, successfully reducing search latency by 20%."
                }
            ]
            
            experience = [
                {
                    "role": "Backend Engineer Intern",
                    "company": "TechCorp",
                    "start_date": "2023-06",
                    "end_date": "2023-12",
                    "bullets": [
                        "Engineered production-grade REST APIs and backend microservices using Python and FastAPI.",
                        "Optimized PostgreSQL queries decreasing search latency by 20% under high load."
                    ]
                }
            ]
            
            return response_schema(
                anchor_line=anchor_line,
                highlights_strip=highlights_strip,
                tailored_experience=experience
            )

        elif schema_name == "TruthfulnessCheckResult":
            is_fabricated = False
            report = []
            
            # Check if prompt contains fabricated claims like Kubernetes cluster management (from test cases)
            if "kubernetes clusters scaling" in text_lower:
                is_fabricated = True
                report.append({
                    "rewritten_bullet": "Managed production Kubernetes clusters scaling up to 100 nodes.",
                    "is_fabricated": True,
                    "justification": "Candidate's original experience only mentions FastAPI and Python backend, not Kubernetes cluster management.",
                    "suggested_fix": "Engineered production-grade REST APIs using Python and FastAPI."
                })
            else:
                report = [
                    {
                        "rewritten_bullet": "Engineered production-grade REST APIs and backend microservices using Python and FastAPI.",
                        "is_fabricated": False,
                        "justification": "",
                        "suggested_fix": ""
                    },
                    {
                        "rewritten_bullet": "Optimized PostgreSQL queries decreasing search latency by 20% under high load.",
                        "is_fabricated": False,
                        "justification": "",
                        "suggested_fix": ""
                    }
                ]
                
            return response_schema(
                is_fabricated=is_fabricated,
                verification_report=report
            )

        elif schema_name == "ResumeParsedData":
            return response_schema(
                name="Eyad Arshad",
                email="eyad.arshad@example.com",
                phone="+92-300-1234567",
                links=["github.com/eyad-dev"],
                skills=["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
                education=[{
                    "degree": "B.S. Computer Science",
                    "school": "NUCES",
                    "date": "2024"
                }],
                experience=[
                    {
                        "role": "Backend Engineer Intern",
                        "company": "TechCorp",
                        "start_date": "2023-06",
                        "end_date": "2023-12",
                        "bullets": [
                            "Developed backend services using Python and FastAPI.",
                            "Optimized database queries decreasing latency by 20%."
                        ]
                    }
                ],
                projects=[]
            )

        # Basic fallback for other schemas
        return response_schema()

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
        if self.api_key and self.api_key.startswith("mock-"):
            logger.info(f"[SIMULATION] Generating structured output for schema {response_schema.__name__}...")
            return self._generate_mock_response(prompt, response_schema)

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
