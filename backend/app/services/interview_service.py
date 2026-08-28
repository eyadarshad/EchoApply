import logging
import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.services.llm_client import llm_client_general as llm_client
from app.services.llm_prompts import INTERVIEW_QUESTIONS_SYSTEM, INTERVIEW_GRADING_SYSTEM

logger = logging.getLogger(__name__)

class InterviewQuestionsSchema(BaseModel):
    questions: List[str] = Field(..., min_length=3, max_length=5, description="List of targeted technical and behavioral interview questions")

class InterviewGradeSchema(BaseModel):
    score: int = Field(..., description="Calculated integer score between 0 and 100 based on STAR structure, technical depth, metrics, and clarity")
    star_compliance: str = Field(..., description="Detailed assessment of Situation, Task, Action, and Result coverage")
    tech_depth: str = Field(..., description="Assessment of technical depth, accuracy, domain competence, and engineering judgment")
    communication_clarity: str = Field(..., description="Assessment of conciseness, articulation, and professional tone")
    constructive_tips: List[str] = Field(default_factory=list, description="2 to 3 actionable, specific bullet-point tips for improvement")

def _evaluate_heuristically(question: str, answer: str) -> Dict[str, Any]:
    """
    Intelligent fallback heuristic evaluation when LLM APIs are offline.
    Dynamically computes a real score based on word count, STAR structure, metrics, and technical keywords.
    """
    words = answer.strip().split()
    word_count = len(words)
    lower_ans = answer.lower()

    # Detect STAR components
    has_situation = any(k in lower_ans for k in ["when", "during", "while at", "project", "situation", "company", "team", "client", "context"])
    has_task = any(k in lower_ans for k in ["goal", "task", "objective", "needed to", "responsible for", "challenge", "problem was", "requirement"])
    has_action = any(k in lower_ans for k in ["i implemented", "i built", "i designed", "i led", "i refactored", "i created", "i analyzed", "i resolved", "i optimized", "i wrote", "i migrated"])
    has_result = any(k in lower_ans for k in ["resulted in", "improved", "increased", "reduced", "decreased", "delivered", "outcome", "saving", "successfully", "launched"])
    
    # Detect metrics & numbers
    has_metrics = bool(re.search(r"\b(\d+(\.\d+)?%|\$\d+|\d+\+?(\s*(ms|s|users|requests|percent|x|times|hours|days|weeks|months|engineers|services)))\b", lower_ans))

    # Base score computation
    score = 40

    if word_count < 25:
        score = max(35, 20 + word_count)
    elif word_count < 60:
        score = 55 + (word_count - 25) // 2
    elif word_count < 150:
        score = 72 + min(15, (word_count - 60) // 6)
    else:
        score = 82 + min(8, (word_count - 150) // 20)

    # STAR bonuses & penalties
    star_matches = sum([has_situation, has_task, has_action, has_result])
    if star_matches == 4:
        score += 8
    elif star_matches == 3:
        score += 4
    elif star_matches <= 1:
        score -= 6

    if has_metrics:
        score += 6
    else:
        score -= 4

    score = max(25, min(96, score))

    # Dynamic feedback generation
    if star_matches >= 3 and has_metrics:
        star_compliance = "Strong structured response covering context, your concrete actions, and a quantifiable outcome."
    elif has_action and not has_result:
        star_compliance = "Good breakdown of actions taken, but missing a clear, measurable Result/Outcome at the end."
    elif not has_situation:
        star_compliance = "Direct answer, but would benefit from setting the initial Situation and business context first."
    else:
        star_compliance = "Partial STAR structure detected. Structure clearly into: 1. Situation, 2. Task, 3. Action, 4. Result."

    if word_count > 80 and (has_action or has_metrics):
        tech_depth = "Good technical substance and concrete details demonstrating relevant domain familiarity."
    elif word_count < 40:
        tech_depth = "Brief overview; expand with specific tools, architectural decisions, and trade-offs made."
    else:
        tech_depth = "Solid high-level overview. Mention specific frameworks, algorithms, or testing strategies."

    communication_clarity = "Concise and easy to follow." if word_count < 180 else "Very thorough, though could be trimmed slightly for tighter delivery."

    tips = []
    if not has_metrics:
        tips.append("Quantify your results (e.g., 'reduced latency by 35%', 'handled 50k DAU', 'saved 10 hours/week').")
    if not has_result:
        tips.append("Conclude with the business impact or what your team learned from the outcome.")
    if word_count < 50:
        tips.append("Expand on your individual contribution vs what the wider team did.")
    if not tips:
        tips.append("Highlight any trade-offs or alternatives you evaluated before choosing your solution.")
        tips.append("Practice delivering this answer aloud within 90-120 seconds.")

    return {
        "score": score,
        "star_compliance": star_compliance,
        "tech_depth": tech_depth,
        "communication_clarity": communication_clarity,
        "constructive_tips": tips[:3]
    }

def generate_mock_questions(profile_data: Dict[str, Any], job_title: str, jd_text: str) -> List[str]:
    """Generate 5 custom behavioral/technical interview questions based on candidate resume and JD."""
    prompt = f"""
    Generate exactly 5 challenging, targeted interview questions for a candidate applying for the role of "{job_title}".
    
    Target Job Description:
    {jd_text[:1500]}
    
    Candidate Resume Profile:
    {json.dumps(profile_data)[:1500]}
    
    Requirements:
    1. Focus on validating the candidate's real achievements and skills mentioned in their resume against the JD requirements.
    2. Mix behavioral (STAR method) and role-specific technical/system design questions.
    3. Return a list of 5 question strings.
    """
    try:
        res = llm_client.generate_structured(
            prompt=prompt,
            response_schema=InterviewQuestionsSchema,
            system_instruction=INTERVIEW_QUESTIONS_SYSTEM
        )
        if res and res.questions and len(res.questions) >= 3:
            return res.questions[:5]
    except Exception as e:
        logger.error(f"Failed to generate structured mock questions: {e}")
        
    # Standard fallback questions if API fails
    return [
        f"Tell me about a time you solved a challenging technical problem relevant to the {job_title} role.",
        "How do you approach learning a new framework or programming language under a tight deadline?",
        "Describe a situation where you had to collaborate with a difficult stakeholder or team member. How did you resolve it?",
        "What is the most interesting project you worked on recently, and what was your specific contribution?",
        "How do you handle testing, debugging, and maintaining code quality in a fast-paced environment?"
    ]

def grade_mock_answer(question: str, answer: str) -> Dict[str, Any]:
    """Grade candidate's mock response dynamically on STAR method, communication, metrics, and technical depth."""
    if not answer or len(answer.strip()) < 10:
        return {
            "score": 30,
            "star_compliance": "Response is too short to evaluate STAR method structure.",
            "tech_depth": "Insufficient detail provided to judge technical competence.",
            "communication_clarity": "Very brief.",
            "constructive_tips": [
                "Provide a complete answer outlining the context, your specific role, and the final outcome.",
                "Aim for 80-150 words using the STAR (Situation, Task, Action, Result) method."
            ]
        }

    prompt = f"""
    You are an expert hiring manager grading an interview response.
    
    Interview Question:
    {question}
    
    Candidate Answer:
    {answer}
    
    Evaluate strictly and dynamically:
    1. score (0-100): Grade truthfully based on depth, relevance, STAR completeness, and metrics.
       - A vague 1-sentence answer should score 35-50.
       - A solid answer with clear actions should score 70-80.
       - An exceptional answer with STAR structure, measurable metrics, and deep domain mastery should score 88-98.
    2. star_compliance: Detailed explanation of Situation, Task, Action, Result coverage.
    3. tech_depth: Evaluation of tools, algorithms, decisions, and problem-solving rigor.
    4. communication_clarity: Conciseness, tone, and delivery.
    5. constructive_tips: 2-3 specific, actionable recommendations.
    """
    try:
        grade = llm_client.generate_structured(
            prompt=prompt,
            response_schema=InterviewGradeSchema,
            system_instruction=INTERVIEW_GRADING_SYSTEM
        )
        if grade and isinstance(grade.score, int):
            return {
                "score": max(0, min(100, grade.score)),
                "star_compliance": grade.star_compliance,
                "tech_depth": grade.tech_depth,
                "communication_clarity": grade.communication_clarity,
                "constructive_tips": grade.constructive_tips or []
            }
    except Exception as e:
        logger.warning(f"Structured grading API failed, falling back to dynamic heuristic evaluator: {e}")
        
    return _evaluate_heuristically(question, answer)

def generate_advanced_interview_prep(profile_data: Dict[str, Any], job_title: str, jd_text: str) -> Dict[str, Any]:
    """
    Generates rich, tailored interview preparation materials:
    - Company/role specific questions based on JD analysis
    - Resume specific questions probing weak areas
    - STAR-format hints/templates
    """
    prompt = f"""
    You are an expert interviewer. Analyze the candidate's resume and target Job Description:
    
    Target Job Description:
    {jd_text[:1500]}
    
    Candidate Resume:
    {json.dumps(profile_data)[:1500]}
    
    Generate the following structured interview prep resources:
    1. 3 Company & Role specific technical/operational questions.
    2. 2 Resume-specific questions targeting potential weak areas, gaps, or critical technologies in the JD that are thin in the resume.
    3. For each of these 5 questions, provide a "STAR-hint" template (Situation, Task, Action, Result) outlining how they should answer.
    
    Output strictly a valid JSON object matching this schema:
    {{
      "company_questions": [
        {{
          "question": "Question text",
          "context": "Why this is critical for the company/role",
          "star_template": {{
            "situation": "What situation to describe",
            "task": "What task to focus on",
            "action": "Actions to highlight",
            "result": "Expected outcomes/metrics to mention"
          }}
        }}
      ],
      "resume_questions": [
        {{
          "question": "Question text",
          "context": "Probing reason (e.g. lack of direct experience in technology X)",
          "star_template": {{
            "situation": "What situation to describe",
            "task": "What task to focus on",
            "action": "Actions to highlight",
            "result": "Expected outcomes/metrics to mention"
          }}
        }}
      ]
    }}
    
    Do not output any markdown formatting, code blocks, or extra text.
    """
    try:
        response_text = llm_client.generate_text(prompt, system_instruction=INTERVIEW_QUESTIONS_SYSTEM).strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response_text)
        if isinstance(data, dict) and ("company_questions" in data or "resume_questions" in data):
            return data
    except Exception as e:
        logger.error(f"Failed to generate advanced interview prep: {e}")
        
    return {
        "company_questions": [
            {
                "question": f"How do you design scalable architectures for systems similar to those in the {job_title} role?",
                "context": "Validates ability to design systems matching target JD scale.",
                "star_template": {
                    "situation": "Describe a system with high traffic or complex data pipelines.",
                    "task": "Explain your mandate to optimize or scale the architecture.",
                    "action": "Details on database choices, caching strategies, and API layers.",
                    "result": "Quantifiable latency reduction or throughput increase."
                }
            }
        ],
        "resume_questions": [
            {
                "question": "The job description emphasizes production deployment and monitoring. Can you describe your hands-on cloud/observability experience?",
                "context": "Probes potential thinness of cloud deployment in your experience.",
                "star_template": {
                    "situation": "Describe a deployment pipeline or outage monitoring scenario.",
                    "task": "Explain your goal to ensure uptime or streamline deployment.",
                    "action": "Discuss tools like Docker, AWS, or Prometheus/Grafana you utilized.",
                    "result": "Uptime metrics, rollback speed, or alert latency improvements."
                }
            }
        ]
    }
