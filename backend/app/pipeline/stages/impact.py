import logging
from typing import List, Dict, Any
from app.schemas import ResumeParsedData, JDAnalysisResult, TargetedRewriteResult, ImpactPassResult, HighlightSkill
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import IMPACT_PASS_SYSTEM

logger = logging.getLogger(__name__)

async def run_impact_pass(
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

    prompt = (
        "Act as an ATS filter and a hiring manager reading 200 resumes in one sitting. Scan my resume to identify which sections get skipped and rewrite them so they actually stop scroll.\n\n"
        f"Target Role: '{jd_analysis.role_title}'\n"
        f"Seniority: {jd_analysis.seniority}\n"
        f"Key Responsibilities: {'; '.join(jd_analysis.key_responsibilities)}\n\n"
        "--- TECHNIQUES TO APPLY ---\n"
    )
    for tech in techniques:
        prompt += f"- {tech.get('technique')}: {tech.get('description')}\n"

    prompt += (
        "\n--- CANDIDATE EXPERIENCES & PROJECTS (WITH TAILORED BULLETS) ---\n"
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
    result = await llm_client.generate_structured_async(
        prompt=prompt,
        response_schema=ImpactPassResult,
        model_type="pro",
        system_instruction=IMPACT_PASS_SYSTEM
    )
    return result
