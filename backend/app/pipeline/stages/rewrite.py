import logging
from app.schemas import ResumeParsedData, GapAnalysisResult, TargetedRewriteResult, RewrittenBullet
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

def rewrite_bullets(profile: ResumeParsedData, gap_analysis: GapAnalysisResult) -> TargetedRewriteResult:
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

    system_instruction = (
        "You are an expert, highly ethical resume writer. Your job is to rewrite a list of resume "
        "experience and project bullet points to better match the target job description terminology, "
        "while strictly maintaining the absolute truth of the candidate's actual achievements. "
        "You must follow these strict rules:\n"
        "1. Do NOT fabricate or embellish any metrics. If the original bullet does not contain a number, "
        "percentage, dollar amount, or project scale, you MUST NOT invent or add one.\n"
        "2. Do NOT add new skills, tools, or responsibilities that the candidate did not mention or imply "
        "in the original bullet.\n"
        "3. Only rephrase or translate terms to align with the JD phrasing (e.g. mapping 'web services' to 'REST APIs' "
        "or 'React.js' to 'React' if the candidate has that skill, or matching Action Verbs to the JD's focus)."
    )

    prompt = (
        "Please rewrite the following list of candidate resume bullet points to better align with the matching keywords.\n\n"
        "--- KEYWORDS TO EMPHASIZE (MATCHED SKILLS) ---\n"
        f"{', '.join(gap_analysis.matched_skills)}\n\n"
        "--- ORIGINAL BULLET POINTS ---\n"
    )
    for i, bullet in enumerate(original_bullets, 1):
        prompt += f"{i}. {bullet}\n"

    prompt += (
        "\nFor each original bullet, output the original text alongside its rewritten, tailored version in the requested JSON structure."
    )

    try:
        logger.info(f"Executing Targeted Rewrite stage for {len(original_bullets)} bullets...")
        result = llm_client.generate_structured(
            prompt=prompt,
            response_schema=TargetedRewriteResult,
            model_type="flash",
            system_instruction=system_instruction
        )
        return result
    except Exception as e:
        logger.error(f"Error during Targeted Rewrite stage: {str(e)}")
        # Fallback: return original bullets unchanged
        fallback_bullets = [
            RewrittenBullet(original_bullet=b, rewritten_bullet=b)
            for b in original_bullets
        ]
        return TargetedRewriteResult(rewritten_bullets=fallback_bullets)
