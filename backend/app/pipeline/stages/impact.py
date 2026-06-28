import logging
from typing import List, Dict, Any
from app.schemas import ResumeParsedData, JDAnalysisResult, TargetedRewriteResult, ImpactPassResult, HighlightSkill
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

def run_impact_pass(
    profile: ResumeParsedData,
    jd_analysis: JDAnalysisResult,
    rewritten_bullets_result: TargetedRewriteResult,
    techniques: List[Dict[str, Any]]
) -> ImpactPassResult:
    """
    Executes the Impact Pass. Escalates to Gemini Pro / high thinking.
    Generates:
      - A tailored anchor line.
      - A highlights strip of top 4-5 relevant skills.
      - A restructured experience section, sorting by metric impact and
        trimming older/weaker bullet points to enforce content density (1-page target).
    """
    # Create a mapping of original bullets to rewritten ones for easy lookup
    bullet_map = {
        b.original_bullet.strip(): b.rewritten_bullet.strip()
        for b in rewritten_bullets_result.rewritten_bullets
    }

    # Map the candidate's experience list, replacing original bullets with rewritten ones
    mapped_experiences = []
    total_bullets = 0
    
    for exp in profile.experience:
        exp_bullets = exp.get("bullets", [])
        new_bullets = []
        for b in exp_bullets:
            mapped_b = bullet_map.get(b.strip(), b.strip())
            new_bullets.append(mapped_b)
        
        mapped_experiences.append({
            "role": exp.get("role", ""),
            "company": exp.get("company", ""),
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
            "location": exp.get("location", ""),
            "bullets": new_bullets
        })
        total_bullets += len(new_bullets)

    # Let's map project bullets too
    mapped_projects = []
    for proj in profile.projects:
        proj_bullets = proj.get("bullets", [])
        new_bullets = []
        for b in proj_bullets:
            mapped_b = bullet_map.get(b.strip(), b.strip())
            new_bullets.append(mapped_b)
        mapped_projects.append({
            "name": proj.get("name", ""),
            "link": proj.get("link", ""),
            "bullets": new_bullets
        })

    # Call LLM to restructure, write anchor tagline, build highlights strip,
    # prioritize, and trim experience/project bullets for a 1-page document target (8-10 bullets max total).
    system_instruction = (
        "You are a professional resume designer. Your task is to apply specific formatting and structural "
        "optimization techniques to compile a high-impact, single-page tailored resume. You must follow "
        "these strict design constraints:\n"
        "1. Anchor Line: Generate a concise tagline (under 80 characters) under the candidate's name that "
        "bridges their core expertise directly to the target role title. Use active, professional phrasing.\n"
        "2. Highlights Strip: Select 4-5 key skills from the candidate's list that match the job description, "
        "and provide a 1-sentence relevance reason showing how the candidate used or matches it.\n"
        "3. Prioritization & Front-loading: For each experience role, reorder the bullet points to lead with the "
        "most impactful, quantified achievements first (e.g. those with percentages, time savings, or revenue metrics).\n"
        "4. Page Budget Trimming: To enforce a strict single-page limit, you must trim weaker, older, or less relevant "
        "bullet points. Each job experience should have at most 3 bullet points, and the total number of experience "
        "bullets across the entire resume must not exceed 8."
    )

    prompt = (
        f"Optimize the candidate's experience and project bullets for a target role of: '{jd_analysis.role_title}'.\n\n"
        "--- TECHNIQUES TO APPLY ---\n"
    )
    for tech in techniques:
        prompt += f"- {tech.get('technique')}: {tech.get('description')}\n"

    prompt += (
        "\n--- JOB DETAILS ---\n"
        f"Role Title: {jd_analysis.role_title}\n"
        f"Seniority: {jd_analysis.seniority}\n"
        f"Key Responsibilities: {'; '.join(jd_analysis.key_responsibilities)}\n\n"
        "--- CANDIDATE EXPERIENCES & PROJECTS (WITH TAILORED BULLETS) ---\n"
        "Experiences:\n"
    )
    for exp in mapped_experiences:
        prompt += f"- Job: {exp['role']} at {exp['company']}\n"
        for b in exp['bullets']:
            prompt += f"  * {b}\n"

    prompt += "\nProjects:\n"
    for proj in mapped_projects:
        prompt += f"- Project: {proj['name']}\n"
        for b in proj['bullets']:
            prompt += f"  * {b}\n"

    prompt += (
        "\nApply the techniques, prioritize the bullets, and trim the lists so they fit the page budget. "
        "Return structured JSON matching the ImpactPassResult schema."
    )

    logger.info("Executing Impact Pass stage (escalating to pro model)...")
    # Run on Pro model for higher quality tagline writing and formatting judgment
    result = llm_client.generate_structured(
        prompt=prompt,
        response_schema=ImpactPassResult,
        model_type="pro",
        system_instruction=system_instruction
    )
    return result
