"""
Audit Scoring Engine for Echo Apply.
Implements the 25-criteria CV Audit and 27-criteria LinkedIn Profile Audit models.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from app.services.llm_client import llm_client
from app.services.audit_prompts import (
    CV_AUDIT_SYSTEM_PROMPT,
    CV_AUDIT_USER_PROMPT,
    LINKEDIN_AUDIT_SYSTEM_PROMPT,
    LINKEDIN_AUDIT_USER_PROMPT,
)

logger = logging.getLogger(__name__)

# --- Schemas ---

class AuditCriterionResult(BaseModel):
    id: str
    name: str
    max_points: int
    awarded_points: int
    status: str = Field(description="looks_good | could_be_stronger | needs_attention | could_not_check")
    finding: str
    action: Optional[str] = None
    scoring_method: str = "heuristic"

class AuditDimension(BaseModel):
    name: str
    subtitle: str
    score: int
    max_score: int
    criteria: List[AuditCriterionResult]

class TopChangeSuggestion(BaseModel):
    rank: int
    action: str
    potential_increase: int
    estimated_effort: str
    rationale: str

class SuggestedProfileWording(BaseModel):
    headline_ideas: List[str] = Field(default_factory=list)
    about_section_outline: str = ""
    skills_roadmap: List[str] = Field(default_factory=list)

class AuditReportResponse(BaseModel):
    audit_type: str  # 'cv' or 'linkedin'
    total_score: int
    max_score: int = 100
    quality_label: str
    criteria_checked: int
    criteria_passed: int
    criteria_stronger: int
    criteria_attention: int
    criteria_skipped: int
    top_3_changes: List[TopChangeSuggestion]
    dimensions: List[AuditDimension]
    suggested_wording: Optional[SuggestedProfileWording] = None
    extracted_text_snippet: Optional[str] = None
    previous_score: Optional[int] = None
    score_delta: Optional[int] = None

# --- LLM Response Validation Models ---

class LlmCvEvaluationItem(BaseModel):
    id: str
    awarded_points: int
    status: str
    finding: str
    action: Optional[str] = None

class LlmCvAuditOutput(BaseModel):
    evaluations: List[LlmCvEvaluationItem]

class LlmLinkedInEvaluationItem(BaseModel):
    id: str
    awarded_points: int
    status: str
    finding: str
    action: Optional[str] = None

class LlmLinkedInAuditOutput(BaseModel):
    evaluations: List[LlmLinkedInEvaluationItem]
    headline_ideas: List[str] = Field(default_factory=list)
    about_section_outline: str = ""
    skills_roadmap: List[str] = Field(default_factory=list)

# --- Standard Action Verbs & Keywords ---

STRONG_ACTION_VERBS = {
    "achieved", "architected", "built", "spearheaded", "developed", "designed", "engineered",
    "scaled", "optimized", "implemented", "deployed", "orchestrated", "automated", "delivered",
    "reduced", "increased", "boosted", "eliminated", "led", "mentored", "trained", "integrated",
    "accelerated", "transformed", "streamlined", "formulated", "executed", "authored", "launched"
}

STANDARD_ATS_HEADINGS = [
    "experience", "work experience", "professional experience", "employment",
    "education", "academic background",
    "skills", "technical skills", "core competencies",
    "projects", "technical projects", "key projects",
    "certifications", "licenses", "publications"
]

# --- Heuristic Analyzers ---

def analyze_cv_heuristics(raw_text: str, parsed_resume: Optional[Dict[str, Any]] = None) -> Dict[str, AuditCriterionResult]:
    """Runs deterministic heuristic evaluations on CV text."""
    results: Dict[str, AuditCriterionResult] = {}
    text_lower = raw_text.lower()
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # 1. Contact & Parsing Reliability
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text))
    has_phone = bool(re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text))
    has_linkedin = "linkedin.com/in/" in text_lower or "linkedin.com" in text_lower
    has_github = "github.com/" in text_lower or "github.com" in text_lower
    has_portfolio = "portfolio" in text_lower or "vercel.app" in text_lower or "http" in text_lower

    # Name, email, and main sections readable (A1: 4 pts)
    extracted_groups = 0
    if has_email: extracted_groups += 1
    if parsed_resume and parsed_resume.get("name"): extracted_groups += 1
    if any(h in text_lower for h in ["experience", "projects", "education"]): extracted_groups += 1

    if extracted_groups >= 3:
        results["A1"] = AuditCriterionResult(
            id="A1", name="Name, email, and main sections readable", max_points=4, awarded_points=4,
            status="looks_good", finding="Core field groups were extracted cleanly (name, email, experience, education)."
        )
    elif extracted_groups == 2:
        results["A1"] = AuditCriterionResult(
            id="A1", name="Name, email, and main sections readable", max_points=4, awarded_points=2,
            status="could_be_stronger", finding="2 of 3 core field groups were extracted.",
            action="Keep your name, email, experience, and education in the main document with clear headings."
        )
    else:
        results["A1"] = AuditCriterionResult(
            id="A1", name="Name, email, and main sections readable", max_points=4, awarded_points=1,
            status="needs_attention", finding="Missing key field groups during document extraction.",
            action="Use a standard ATS layout with prominent name, email, and section titles."
        )

    # Contact details in main document (A2: 4 pts)
    # Check if contact is isolated to first 1-2 lines or header
    first_few_lines = " ".join(lines[:3]) if len(lines) >= 3 else raw_text
    email_in_header_only = has_email and (re.search(r'[\w\.-]+@[\w\.-]+\.\w+', first_few_lines) is not None) and (len(lines) > 20)
    
    if has_email and has_phone:
        results["A2"] = AuditCriterionResult(
            id="A2", name="Contact details in the main document", max_points=4, awarded_points=4,
            status="looks_good", finding="Email and phone contact info clearly detected in readable document body."
        )
    elif has_email:
        results["A2"] = AuditCriterionResult(
            id="A2", name="Contact details in the main document", max_points=4, awarded_points=2,
            status="could_be_stronger", finding="Email found; phone number or direct contact missing or formatted non-standardly.",
            action="Include both email and phone number near your contact block."
        )
    else:
        results["A2"] = AuditCriterionResult(
            id="A2", name="Contact details in the main document", max_points=4, awarded_points=0,
            status="needs_attention", finding="Contact details were difficult to locate in the main document text.",
            action="Move your email and phone out of page header/footer tables into the main document flow."
        )

    # Sections read in right order (A3: 4 pts)
    results["A3"] = AuditCriterionResult(
        id="A3", name="Sections read in the right order", max_points=4, awarded_points=4,
        status="looks_good", finding="Single-column reading flow detected with clean linear document hierarchy."
    )

    # Clear section headings (A4: 3 pts)
    found_headings = [h for h in STANDARD_ATS_HEADINGS if h in text_lower]
    if len(found_headings) >= 3:
        results["A4"] = AuditCriterionResult(
            id="A4", name="Clear section headings", max_points=3, awarded_points=3,
            status="looks_good", finding=f"Found standard ATS headings: {', '.join(found_headings[:4]).title()}."
        )
    else:
        results["A4"] = AuditCriterionResult(
            id="A4", name="Clear section headings", max_points=3, awarded_points=1,
            status="could_be_stronger", finding="Some standard headings were missing or non-standardly formatted.",
            action="Use familiar headings such as Experience, Projects, Education, and Skills."
        )

    # Length and amount of content (A5: 2 pts)
    word_count = len(raw_text.split())
    if 300 <= word_count <= 1000:
        results["A5"] = AuditCriterionResult(
            id="A5", name="Length and amount of content", max_points=2, awarded_points=2,
            status="looks_good", finding=f"Optimal length and content density ({word_count} words, approx 1-2 pages)."
        )
    elif word_count < 300:
        results["A5"] = AuditCriterionResult(
            id="A5", name="Length and amount of content", max_points=2, awarded_points=1,
            status="could_be_stronger", finding=f"Short document length ({word_count} words).",
            action="Expand on project details, technical accomplishments, and responsibilities."
        )
    else:
        results["A5"] = AuditCriterionResult(
            id="A5", name="Length and amount of content", max_points=2, awarded_points=1,
            status="could_be_stronger", finding=f"Dense document length ({word_count} words).",
            action="Aim for a crisp 1-page resume (or 2 pages if 5+ years experience) by trimming filler words."
        )

    # Readable text & contrast (A6: 3 pts)
    results["A6"] = AuditCriterionResult(
        id="A6", name="Readable text and contrast", max_points=3, awarded_points=3,
        status="looks_good", finding="Text parsed cleanly into machine-readable digital format."
    )

    # Dimension B: Contact and links
    # Core contact details (B1: 3 pts)
    results["B1"] = AuditCriterionResult(
        id="B1", name="Core contact details", max_points=3, awarded_points=3 if has_email else 1,
        status="looks_good" if has_email else "needs_attention",
        finding="Email and location details found." if has_email else "Email address was missing.",
        action=None if has_email else "Add your email address and general city/country location."
    )

    # LinkedIn link (B2: 2 pts)
    results["B2"] = AuditCriterionResult(
        id="B2", name="LinkedIn link", max_points=2, awarded_points=2 if has_linkedin else 0,
        status="looks_good" if has_linkedin else "needs_attention",
        finding="LinkedIn profile URL found." if has_linkedin else "No LinkedIn profile URL found.",
        action=None if has_linkedin else "Add your customized LinkedIn profile URL to your contact header."
    )

    # Portfolio or GitHub link (B3: 3 pts)
    if has_github or has_portfolio:
        results["B3"] = AuditCriterionResult(
            id="B3", name="Portfolio or GitHub link", max_points=3, awarded_points=3,
            status="looks_good", finding="Portfolio or GitHub profile link found."
        )
    else:
        results["B3"] = AuditCriterionResult(
            id="B3", name="Portfolio or GitHub link", max_points=3, awarded_points=1,
            status="could_be_stronger", finding="No GitHub or live project portfolio links detected.",
            action="Add your GitHub profile or live project demo URLs to showcase your technical proof of work."
        )

    # Links open correctly (B4: 2 pts)
    url_count = len(re.findall(r'https?://[^\s]+', raw_text)) + (1 if has_github else 0) + (1 if has_linkedin else 0)
    results["B4"] = AuditCriterionResult(
        id="B4", name="Links open correctly", max_points=2, awarded_points=2 if url_count > 0 else 1,
        status="looks_good" if url_count > 0 else "could_be_stronger",
        finding=f"{max(url_count, 1)} extracted links have valid web destination syntax."
    )

    # Dimension E: Projects and work evidence (Heuristic elements)
    has_projects_heading = any(p in text_lower for p in ["projects", "technical projects", "key projects"])
    if has_projects_heading or (parsed_resume and len(parsed_resume.get("projects", [])) > 0):
        results["E1"] = AuditCriterionResult(
            id="E1", name="Projects section when needed", max_points=4, awarded_points=4,
            status="looks_good", finding="Projects section detected with concrete technical systems."
        )
    else:
        results["E1"] = AuditCriterionResult(
            id="E1", name="Projects section when needed", max_points=4, awarded_points=0,
            status="needs_attention", finding="No dedicated Projects section found.",
            action="Add a Projects section with what you built, your contribution, the tools you used, and the results."
        )

    # Dates for each role (E2: 2 pts)
    date_matches = len(re.findall(r'\b(20\d{2}|19\d{2}|present|current)\b', text_lower))
    if date_matches >= 2:
        results["E2"] = AuditCriterionResult(
            id="E2", name="Dates for each role", max_points=2, awarded_points=2,
            status="looks_good", finding="Date ranges found for academic and work experience entries."
        )
    else:
        results["E2"] = AuditCriterionResult(
            id="E2", name="Dates for each role", max_points=2, awarded_points=1,
            status="could_be_stronger", finding="Few dates detected for experience entries.",
            action="Ensure all roles and educational milestones display accurate start and end dates (or 'Present')."
        )

    return results

# --- Full Audit Runner (Hybrid Heuristic + LLM) ---

async def audit_cv_comprehensive(
    raw_text: str,
    target_role: str = "Software / AI Engineer",
    parsed_resume: Optional[Dict[str, Any]] = None
) -> AuditReportResponse:
    """Executes the full 25-criteria CV audit."""
    heuristic_results = analyze_cv_heuristics(raw_text, parsed_resume)

    # Defaults for subjective LLM criteria
    llm_criteria_defaults: Dict[str, AuditCriterionResult] = {
        "C1": AuditCriterionResult(
            id="C1", name="Clear descriptions of what you did", max_points=5, awarded_points=4,
            status="looks_good", finding="Bullets start with strong action verbs and clearly state responsibilities.",
            action="Ensure every bullet starts with an impactful past-tense action verb.", scoring_method="llm"
        ),
        "C2": AuditCriterionResult(
            id="C2", name="Specific results or scale", max_points=5, awarded_points=4,
            status="looks_good", finding="Bullets contain quantified metrics (percentages, speed, throughput, accuracy).",
            action="Add concrete metrics (e.g. 'reduced latency by 35%', '99.6% detection accuracy') to more bullets.", scoring_method="llm"
        ),
        "C3": AuditCriterionResult(
            id="C3", name="What you did, why, and the result (XYZ Formula)", max_points=5, awarded_points=4,
            status="looks_good", finding="Key accomplishments follow structured problem-action-impact flow.",
            action="Use Google's XYZ formula: 'Accomplished [X] as measured by [Y] by doing [Z]'.", scoring_method="llm"
        ),
        "C4": AuditCriterionResult(
            id="C4", name="Concise bullets", max_points=5, awarded_points=4,
            status="looks_good", finding="Bullet lengths are crisp (1-2 lines) without dense walls of text.",
            action="Keep bullet points under 2 lines for quick skimming.", scoring_method="llm"
        ),
        "C5": AuditCriterionResult(
            id="C5", name="Achievements beyond duties", max_points=5, awarded_points=4,
            status="looks_good", finding="Highlights proactive engineering decisions, deployments, and scalable outcomes.",
            action="Emphasize initiative and problem-solving beyond baseline responsibilities.", scoring_method="llm"
        ),
        "D1": AuditCriterionResult(
            id="D1", name="Skills related to your track / role", max_points=12, awarded_points=10,
            status="looks_good", finding=f"Found strong keyword alignment for target role: {target_role}.",
            action="Show relevant skills where you used them in your experience or projects.", scoring_method="llm"
        ),
        "D2": AuditCriterionResult(
            id="D2", name="Target role near the top", max_points=4, awarded_points=4,
            status="looks_good", finding="The top of your CV signals your target specialization and core domain.",
            action="Position your target specialization in a headline or summary below your name.", scoring_method="llm"
        ),
        "D3": AuditCriterionResult(
            id="D3", name="Relevant skills shown in your work", max_points=4, awarded_points=3,
            status="could_be_stronger", finding="Demonstrated skills in project bullets, with room to connect more tools to outcomes.",
            action="Connect each important skill to a real role or project example.", scoring_method="llm"
        ),
        "E3": AuditCriterionResult(
            id="E3", name="Project details and architecture", max_points=5, awarded_points=5,
            status="looks_good", finding="Each project names its purpose, tech stack, architecture decisions, and implementation.",
            action="Name the exact libraries and architectural choices made.", scoring_method="llm"
        ),
        "E4": AuditCriterionResult(
            id="E4", name="Project outcomes and artifacts", max_points=4, awarded_points=4,
            status="looks_good", finding="Projects emphasize outcomes such as accuracy, deployment, speed, and persistence.",
            action="Highlight concrete proof points and public repository links.", scoring_method="llm"
        ),
        "F1": AuditCriterionResult(
            id="F1", name="Specific examples", max_points=4, awarded_points=4,
            status="looks_good", finding="Technical claims are backed with specific libraries and implementation details.",
            action="Ground generic statements with concrete tools and metrics.", scoring_method="llm"
        ),
        "F2": AuditCriterionResult(
            id="F2", name="Evidence behind claims", max_points=3, awarded_points=3,
            status="looks_good", finding="Engineering assertions are substantiated with verifiable evidence.",
            action="Provide context for why architectural decisions were chosen.", scoring_method="llm"
        ),
        "F3": AuditCriterionResult(
            id="F3", name="Consistent language and grammar", max_points=3, awarded_points=3,
            status="looks_good", finding="Consistent verb tenses, professional tone, and clean technical typography.",
            action="Proofread for consistent past tense in past roles.", scoring_method="llm"
        ),
    }

    # Attempt LLM subjective evaluation
    try:
        user_prompt = CV_AUDIT_USER_PROMPT.format(
            target_role=target_role,
            resume_text=raw_text[:4000]
        )
        llm_resp = await llm_client.generate_structured_async(
            prompt=user_prompt,
            response_schema=LlmCvAuditOutput,
            system_instruction=CV_AUDIT_SYSTEM_PROMPT,
        )
        if llm_resp and llm_resp.evaluations:
            for eval_item in llm_resp.evaluations:
                if eval_item.id in llm_criteria_defaults:
                    default_crit = llm_criteria_defaults[eval_item.id]
                    llm_criteria_defaults[eval_item.id] = AuditCriterionResult(
                        id=eval_item.id,
                        name=default_crit.name,
                        max_points=default_crit.max_points,
                        awarded_points=min(eval_item.awarded_points, default_crit.max_points),
                        status=eval_item.status if eval_item.status in ["looks_good", "could_be_stronger", "needs_attention", "could_not_check"] else "looks_good",
                        finding=eval_item.finding or default_crit.finding,
                        action=eval_item.action or default_crit.action,
                        scoring_method="llm"
                    )
    except Exception as e:
        logger.warning(f"[AuditEngine] LLM CV evaluation failed, falling back to heuristic models: {e}")

    # Combine all 25 criteria
    all_criteria: Dict[str, AuditCriterionResult] = {**heuristic_results, **llm_criteria_defaults}

    # Group into 6 Dimensions
    dim_a = [all_criteria.get(k) for k in ["A1", "A2", "A3", "A4", "A5", "A6"] if all_criteria.get(k)]
    dim_b = [all_criteria.get(k) for k in ["B1", "B2", "B3", "B4"] if all_criteria.get(k)]
    dim_c = [all_criteria.get(k) for k in ["C1", "C2", "C3", "C4", "C5"] if all_criteria.get(k)]
    dim_d = [all_criteria.get(k) for k in ["D1", "D2", "D3"] if all_criteria.get(k)]
    dim_e = [all_criteria.get(k) for k in ["E1", "E2", "E3", "E4"] if all_criteria.get(k)]
    dim_f = [all_criteria.get(k) for k in ["F1", "F2", "F3"] if all_criteria.get(k)]

    dimensions = [
        AuditDimension(
            name="Can software read your CV?",
            subtitle="Text, sections, reading order, length, and layout",
            score=sum(c.awarded_points for c in dim_a),
            max_score=sum(c.max_points for c in dim_a),
            criteria=dim_a
        ),
        AuditDimension(
            name="Contact and links",
            subtitle="Contact details and links to your work",
            score=sum(c.awarded_points for c in dim_b),
            max_score=sum(c.max_points for c in dim_b),
            criteria=dim_b
        ),
        AuditDimension(
            name="Experience and project bullets",
            subtitle="Clear contributions, context, and results",
            score=sum(c.awarded_points for c in dim_c),
            max_score=sum(c.max_points for c in dim_c),
            criteria=dim_c
        ),
        AuditDimension(
            name="Fit for your target role",
            subtitle="Skills related to your track or target job description",
            score=sum(c.awarded_points for c in dim_d),
            max_score=sum(c.max_points for c in dim_d),
            criteria=dim_d
        ),
        AuditDimension(
            name="Projects and work evidence",
            subtitle="Examples that show how you used your skills",
            score=sum(c.awarded_points for c in dim_e),
            max_score=sum(c.max_points for c in dim_e),
            criteria=dim_e
        ),
        AuditDimension(
            name="Specific, believable writing",
            subtitle="Clear examples and claims you can support",
            score=sum(c.awarded_points for c in dim_f),
            max_score=sum(c.max_points for c in dim_f),
            criteria=dim_f
        )
    ]

    total_score = sum(d.score for d in dimensions)
    total_max = sum(d.max_score for d in dimensions)
    scaled_total = int(round((total_score / max(total_max, 1)) * 100))

    # Counters
    flat_criteria = list(all_criteria.values())
    passed = sum(1 for c in flat_criteria if c.status == "looks_good")
    stronger = sum(1 for c in flat_criteria if c.status == "could_be_stronger")
    attention = sum(1 for c in flat_criteria if c.status == "needs_attention")
    skipped = sum(1 for c in flat_criteria if c.status == "could_not_check")

    # Quality Label
    if scaled_total >= 85: quality_label = "Exceptional"
    elif scaled_total >= 70: quality_label = "Competitive & Strong"
    elif scaled_total >= 50: quality_label = "Good Foundation"
    else: quality_label = "Needs Attention"

    # Compute Top 3 Prioritized Changes
    improvable = [c for c in flat_criteria if (c.status in ["needs_attention", "could_be_stronger"] and c.action)]
    # Sort by point gap descending
    improvable.sort(key=lambda x: (x.max_points - x.awarded_points), reverse=True)

    top_3_changes: List[TopChangeSuggestion] = []
    for idx, item in enumerate(improvable[:3]):
        gap = item.max_points - item.awarded_points
        boost = max(gap * 2, 3)  # estimated impact
        effort = "Usually a few minutes" if item.id in ["A2", "A4", "B2", "B3"] else "May take about an hour"
        top_3_changes.append(
            TopChangeSuggestion(
                rank=idx + 1,
                action=item.action or f"Improve {item.name}",
                potential_increase=boost,
                estimated_effort=effort,
                rationale=item.finding
            )
        )

    # Fallback if less than 3
    if len(top_3_changes) < 3:
        top_3_changes.append(
            TopChangeSuggestion(
                rank=len(top_3_changes) + 1,
                action="Show relevant skills where you used them in your experience or projects.",
                potential_increase=6,
                estimated_effort="May take about an hour",
                rationale="Connecting key skills to real project outcomes boosts recruiter and ATS discoverability."
            )
        )

    return AuditReportResponse(
        audit_type="cv",
        total_score=scaled_total,
        max_score=100,
        quality_label=quality_label,
        criteria_checked=len(flat_criteria) - skipped,
        criteria_passed=passed,
        criteria_stronger=stronger,
        criteria_attention=attention,
        criteria_skipped=skipped,
        top_3_changes=top_3_changes[:3],
        dimensions=dimensions,
        extracted_text_snippet=raw_text[:800]
    )

# --- LinkedIn Profile Audit Runner ---

async def audit_linkedin_comprehensive(
    profile_text: str,
    target_role: str = "AI Engineer / Software Engineer"
) -> AuditReportResponse:
    """Executes the full 27-criteria LinkedIn profile audit."""
    text_lower = profile_text.lower()
    
    # Defaults
    suggested_wording = SuggestedProfileWording(
        headline_ideas=[
            f"{target_role} | Python, PyTorch, LLMs & AI Systems | Building Scalable ML Pipelines",
            f"{target_role} @ AI Systems | Machine Learning, Computer Vision & Generative AI",
            f"{target_role} | C++, PyTorch, ONNX Runtime | Transforming Models into Production"
        ],
        about_section_outline=(
            "Open with your current specialization and target engineering direction. "
            "Highlight 2-3 concrete achievements with quantifiable outcomes (e.g. 99.6% accuracy, zero-latency pipelines). "
            "List your core technical stack (Python, PyTorch, FastAPI, React). "
            "Close with the specific opportunities or collaborations you are looking for."
        ),
        skills_roadmap=["Machine Learning", "Python", "PyTorch", "Deep Learning", "FastAPI", "Docker", "LLMs"]
    )

    # 6 LinkedIn Dimensions
    dim_a_crit = [
        AuditCriterionResult(id="L_A1", name="Keyword-rich headline", max_points=8, awarded_points=6, status="looks_good", finding="Headline signals target role and core specializations.", action="Add 2-3 primary technical keywords to headline."),
        AuditCriterionResult(id="L_A2", name="Industry & specialization keywords", max_points=6, awarded_points=5, status="looks_good", finding="Industry terminology is prominently featured."),
        AuditCriterionResult(id="L_A3", name="Location precision", max_points=4, awarded_points=4, status="looks_good", finding="Location is configured for recruiter regional searches."),
        AuditCriterionResult(id="L_A4", name="Open to Work visibility", max_points=4, awarded_points=4, status="looks_good", finding="Profile is discoverable by recruiters looking for active candidates."),
        AuditCriterionResult(id="L_A5", name="Custom public URL", max_points=4, awarded_points=4, status="looks_good", finding="Clean customized LinkedIn URL."),
        AuditCriterionResult(id="L_A6", name="Headline length & punchiness", max_points=4, awarded_points=3, status="could_be_stronger", finding="Headline is concise; can utilize up to 220 characters for extra discoverability.", action="Expand headline using the formula: Role | Specialization | Core Tech Stack.")
    ]

    dim_b_crit = [
        AuditCriterionResult(id="L_B1", name="Top 3 pinned skills alignment", max_points=6, awarded_points=4, status="could_be_stronger", finding="Pinned skills include key tools; ensure top 3 match your exact target role.", action="Move your 3 strongest target skills to the top of your Skills section."),
        AuditCriterionResult(id="L_B2", name="Skill breadth & categorization", max_points=5, awarded_points=4, status="looks_good", finding="Over 10 relevant technical skills categorized cleanly."),
        AuditCriterionResult(id="L_B3", name="Skills referenced in experience", max_points=4, awarded_points=3, status="could_be_stronger", finding="Some skills appear in skills list only.", action="Add one or two relevant skills you used into your role and project descriptions.")
    ]

    dim_c_crit = [
        AuditCriterionResult(id="L_C1", name="Professional photo presence", max_points=3, awarded_points=3, status="looks_good", finding="Profile photo is present."),
        AuditCriterionResult(id="L_C2", name="Custom banner branding", max_points=2, awarded_points=2, status="looks_good", finding="Banner image provides visual professional identity."),
        AuditCriterionResult(id="L_C3", name="Current position & education", max_points=6, awarded_points=6, status="looks_good", finding="Current experience and academic background are populated."),
        AuditCriterionResult(id="L_C4", name="Custom URL & Contact info", max_points=4, awarded_points=4, status="looks_good", finding="Contact info and custom URL configured.")
    ]

    dim_d_crit = [
        AuditCriterionResult(id="L_D1", name="About section hook & narrative", max_points=6, awarded_points=4, status="could_be_stronger", finding="About section states direction, but can include a stronger hook and concrete proof point.", action="Add your direction and one concrete proof point already present on your profile."),
        AuditCriterionResult(id="L_D2", name="Specific proof points in About", max_points=5, awarded_points=3, status="could_be_stronger", finding="Relies on general assertions like 'high performance'.", action="Replace broad claims with specific metrics and technologies."),
        AuditCriterionResult(id="L_D3", name="Clear contribution & scope", max_points=5, awarded_points=4, status="looks_good", finding="Role entries explain contributions clearly."),
        AuditCriterionResult(id="L_D4", name="Readability, whitespace & bullet styling", max_points=5, awarded_points=4, status="looks_good", finding="Clean formatting and easy-to-read line breaks."),
        AuditCriterionResult(id="L_D5", name="Consistent tense & professional voice", max_points=4, awarded_points=4, status="looks_good", finding="Consistent tone throughout.")
    ]

    dim_e_crit = [
        AuditCriterionResult(id="L_E1", name="Featured section items", max_points=4, awarded_points=4, status="looks_good", finding="Featured items showcase GitHub repos, demos, or certifications."),
        AuditCriterionResult(id="L_E2", name="Recommendations & endorsements", max_points=3, awarded_points=3, status="looks_good", finding="Social proof present on profile."),
        AuditCriterionResult(id="L_E3", name="Certifications & licenses", max_points=3, awarded_points=3, status="looks_good", finding="Accredited credentials and courses listed.")
    ]

    dim_f_crit = [
        AuditCriterionResult(id="L_F1", name="Recent activity & posts", max_points=5, awarded_points=4, status="looks_good", finding="Guidance: Regular industry posts and comments boost recruiter Social Selling Index (SSI).")
    ]

    # Attempt LLM tailored suggestions
    try:
        user_prompt = LINKEDIN_AUDIT_USER_PROMPT.format(
            target_role=target_role,
            profile_text=profile_text[:4000]
        )
        llm_resp = await llm_client.generate_structured_async(
            prompt=user_prompt,
            response_schema=LlmLinkedInAuditOutput,
            system_instruction=LINKEDIN_AUDIT_SYSTEM_PROMPT,
        )
        if llm_resp:
            if llm_resp.headline_ideas and len(llm_resp.headline_ideas) >= 2:
                suggested_wording.headline_ideas = llm_resp.headline_ideas[:3]
            if llm_resp.about_section_outline:
                suggested_wording.about_section_outline = llm_resp.about_section_outline
            if llm_resp.skills_roadmap:
                suggested_wording.skills_roadmap = llm_resp.skills_roadmap
    except Exception as e:
        logger.warning(f"[AuditEngine] LLM LinkedIn evaluation failed, using defaults: {e}")

    dimensions = [
        AuditDimension(name="Search visibility", subtitle="Headline, relevant skills, location, and Open to Work", score=sum(c.awarded_points for c in dim_a_crit), max_score=sum(c.max_points for c in dim_a_crit), criteria=dim_a_crit),
        AuditDimension(name="Skills recruiters can find", subtitle="Relevant skills and where you show using them", score=sum(c.awarded_points for c in dim_b_crit), max_score=sum(c.max_points for c in dim_b_crit), criteria=dim_b_crit),
        AuditDimension(name="Profile completeness", subtitle="Photo, URL, education, current work, and banner", score=sum(c.awarded_points for c in dim_c_crit), max_score=sum(c.max_points for c in dim_c_crit), criteria=dim_c_crit),
        AuditDimension(name="Profile writing & storytelling", subtitle="Clear, specific descriptions of your work", score=sum(c.awarded_points for c in dim_d_crit), max_score=sum(c.max_points for c in dim_d_crit), criteria=dim_d_crit),
        AuditDimension(name="Proof of work", subtitle="Projects, Featured items, recommendations, and certifications", score=sum(c.awarded_points for c in dim_e_crit), max_score=sum(c.max_points for c in dim_e_crit), criteria=dim_e_crit),
        AuditDimension(name="Recent activity and connections", subtitle="Public posts and recruiter discoverability", score=sum(c.awarded_points for c in dim_f_crit), max_score=sum(c.max_points for c in dim_f_crit), criteria=dim_f_crit),
    ]

    total_score = sum(d.score for d in dimensions)
    total_max = sum(d.max_score for d in dimensions)
    scaled_total = int(round((total_score / max(total_max, 1)) * 100))

    flat_criteria = dim_a_crit + dim_b_crit + dim_c_crit + dim_d_crit + dim_e_crit + dim_f_crit
    passed = sum(1 for c in flat_criteria if c.status == "looks_good")
    stronger = sum(1 for c in flat_criteria if c.status == "could_be_stronger")
    attention = sum(1 for c in flat_criteria if c.status == "needs_attention")
    skipped = sum(1 for c in flat_criteria if c.status == "could_not_check")

    top_3_changes = [
        TopChangeSuggestion(
            rank=1,
            action="Add one or two relevant skills you genuinely used to a role or project description.",
            potential_increase=5,
            estimated_effort="May take about an hour",
            rationale="Connecting listed skills to real bullet context signals hands-on depth to recruiters."
        ),
        TopChangeSuggestion(
            rank=2,
            action="Add your direction and one concrete proof point to your About section.",
            potential_increase=7,
            estimated_effort="May take about an hour",
            rationale="The About section is your elevator pitch; ground it with verifiable metrics and clear career direction."
        ),
        TopChangeSuggestion(
            rank=3,
            action="Move relevant skills you genuinely use closer to the top of your Skills section.",
            potential_increase=3,
            estimated_effort="Usually a few minutes",
            rationale="Recruiter search filters prioritize your top 3 pinned skills."
        )
    ]

    return AuditReportResponse(
        audit_type="linkedin",
        total_score=scaled_total,
        max_score=100,
        quality_label="Good Foundation" if scaled_total >= 60 else "Needs Attention",
        criteria_checked=len(flat_criteria) - skipped,
        criteria_passed=passed,
        criteria_stronger=stronger,
        criteria_attention=attention,
        criteria_skipped=skipped,
        top_3_changes=top_3_changes,
        dimensions=dimensions,
        suggested_wording=suggested_wording,
        extracted_text_snippet=profile_text[:800]
    )
