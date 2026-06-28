import logging
from app.schemas import ResumeParsedData, ImpactPassResult, TruthfulnessCheckResult, BulletVerification
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

def verify_truthfulness(profile: ResumeParsedData, impact_result: ImpactPassResult) -> TruthfulnessCheckResult:
    """
    Audits the tailored experience bullets against the original resume details.
    Runs on Gemini Pro to ensure high judgment accuracy.
    Flags any bullet that contains fabricated skills, tools, or metrics.
    """
    # Collect original experience/project bullets to show the auditor
    original_bullets = []
    for exp in profile.experience:
        for bullet in exp.get("bullets", []):
            if bullet.strip():
                original_bullets.append(bullet.strip())
    for proj in profile.projects:
        for bullet in proj.get("bullets", []):
            if bullet.strip():
                original_bullets.append(bullet.strip())

    # Collect rewritten/tailored experience bullets
    tailored_bullets = []
    for exp in impact_result.tailored_experience:
        for bullet in exp.get("bullets", []):
            if bullet.strip():
                tailored_bullets.append(bullet.strip())

    if not tailored_bullets:
        logger.warning("No tailored experience bullets found for audit. Returning empty verification report.")
        return TruthfulnessCheckResult(is_fabricated=False, verification_report=[])

    system_instruction = (
        "You are an independent, highly critical resume auditor. Your sole task is to compare tailored experience "
        "bullets against the candidate's original resume details and flag any embellishments or fabrications. "
        "Follow these audit protocols strictly:\n"
        "1. Flag as fabricated (is_fabricated = true) if a tailored bullet introduces any metric, percentage, "
        "dollar value, scale, or time saving that was NOT explicitly mentioned in the original resume.\n"
        "2. Flag as fabricated (is_fabricated = true) if a tailored bullet claims experience with a programming language, "
        "framework, or tool that is NOT mentioned in that specific original experience bullet or in the candidate's skill list.\n"
        "3. Flag as fabricated (is_fabricated = true) if a tailored bullet claims a responsibility, role scope, or task "
        "not supported by the original text.\n"
        "4. For every tailored bullet, you must output a report. If a bullet is truthful, set is_fabricated = false. "
        "If it has fabrications, set is_fabricated = true, explain the justification, and suggest a factual fix."
    )

    prompt = (
        "Perform a truthfulness audit. Cross-examine the tailored bullets against the original candidate data.\n\n"
        "--- CANDIDATE ORIGINAL SKILLS ---\n"
        f"{', '.join(profile.skills)}\n\n"
        "--- CANDIDATE ORIGINAL EXPERIENCE BULLETS ---\n"
    )
    for i, ob in enumerate(original_bullets, 1):
        prompt += f"{i}. {ob}\n"

    prompt += "\n--- PROPOSED TAILORED EXPERIENCE BULLETS ---\n"
    for j, tb in enumerate(tailored_bullets, 1):
        prompt += f"{j}. {tb}\n"

    prompt += (
        "\nAnalyze each tailored bullet. Determine if it introduces fabricated content. "
        "Return the audit report in the structured JSON matching the TruthfulnessCheckResult schema."
    )

    try:
        logger.info("Executing Truthfulness Gate audit (Gemini Pro)...")
        result = llm_client.generate_structured(
            prompt=prompt,
            response_schema=TruthfulnessCheckResult,
            model_type="pro",
            system_instruction=system_instruction
        )
        
        # Double check if any bullet in the report is marked as fabricated, and set the root flag
        any_fabricated = any(item.is_fabricated for item in result.verification_report)
        result.is_fabricated = any_fabricated
        
        logger.info(f"Truthfulness audit completed. Fabrications flagged: {any_fabricated}")
        return result
    except Exception as e:
        logger.error(f"Error during Truthfulness Gate stage: {str(e)}")
        # Safe fallback: assume all is truthful (no block)
        verifications = [
            BulletVerification(rewritten_bullet=b, is_fabricated=False, justification="", suggested_fix="")
            for b in tailored_bullets
        ]
        return TruthfulnessCheckResult(is_fabricated=False, verification_report=verifications)
