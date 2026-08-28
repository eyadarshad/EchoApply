import logging
from app.schemas import ResumeParsedData, GapAnalysisResult, TargetedRewriteResult, RewrittenBullet
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import REWRITE_SYSTEM

logger = logging.getLogger(__name__)

async def rewrite_bullets(profile: ResumeParsedData, gap_analysis: GapAnalysisResult) -> TargetedRewriteResult:
    """
    Rephrases the candidate's experience and project bullets to emphasize
    matching skills/keywords. Strictly restricted to facts in the original resume.
    """
    # Collect all bullets from experiences and projects
    original_bullets = []
    for exp in profile.experience:
        for bullet in exp.get("bullets", []):
            if bullet.strip():
                original_bullets.append(bullet.strip())
                
    for proj in profile.projects:
        for bullet in proj.get("bullets", []):
            if bullet.strip():
                original_bullets.append(bullet.strip())

    if not original_bullets:
        logger.warning("No experience or project bullets found. Returning empty rewrite result.")
        return TargetedRewriteResult(rewritten_bullets=[])

    prompt = (
        "Recreate my resume and naturally remove those red flags. Use the Google X-Y-Z formula: Accomplish X as measured by Y by doing Z.\n\n"
        "--- RED FLAGS TO ELIMINATE ---\n"
        f"{', '.join(gap_analysis.red_flags or [])}\n\n"
        "--- KEYWORDS TO EMPHASIZE (MATCHED SKILLS) ---\n"
        f"{', '.join(gap_analysis.matched_skills)}\n\n"
        "--- ORIGINAL BULLET POINTS ---\n"
    )
    for i, bullet in enumerate(original_bullets, 1):
        prompt += f"{i}. {bullet}\n"

    prompt += (
        "\nFor each original bullet, output the original text alongside its rewritten, tailored version in the requested JSON structure."
    )

    logger.info(f"Executing Targeted Rewrite stage for {len(original_bullets)} bullets...")
    result = await llm_client.generate_structured_async(
        prompt=prompt,
        response_schema=TargetedRewriteResult,
        model_type="flash",
        system_instruction=REWRITE_SYSTEM
    )
    return result
