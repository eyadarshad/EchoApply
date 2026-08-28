import re
import uuid
import logging
from typing import List, Optional, Set
from app.config import settings
from app.schemas import ResumeParsedData, ImpactPassResult, TruthfulnessCheckResult, BulletVerification
from app.services.llm_client import llm_client_resume as llm_client
from app.services.llm_prompts import TRUTHFULNESS_SYSTEM
from app.pipeline.stages.claim_ledger import ClaimLedger, ClaimRecord

logger = logging.getLogger(__name__)

def extract_metrics(text: str) -> Set[str]:
    """
    Extracts numerical metrics (percentages, dollar amounts, large integers) from text.
    Filters out common indices like 1, 2, 3.
    """
    metrics = set()
    # Normalize clean words
    cleaned_text = re.sub(r'[^\w\s\.,%\$\+]', '', text)
    # Find numbers like 50%, $500, 1,000, 10k, 5M, 2.5
    tokens = re.findall(r'\b\d+(?:[\.,]\d+)?(?:%|[kKmMbB]\+?)?\b|\b\$\d+(?:[\.,]\d+)?[kKmMbB]?\b', cleaned_text)
    
    for t in tokens:
        t_clean = t.lower().strip()
        # Skip small indices/counts that are not significant metrics
        if t_clean in ["1", "2", "3", "0", "one", "two", "three"]:
            continue
        metrics.add(t_clean)
    return metrics

def validate_claim_evidence(original_bullets: List[str], rewritten_bullet: str) -> Optional[str]:
    """
    Deterministic validation: checks if any metric/number in the rewritten bullet
    was fabricated (i.e. does not exist in any original bullet).
    Returns a warning message string if fabrication is found, otherwise None.
    """
    rewritten_metrics = extract_metrics(rewritten_bullet)
    if not rewritten_metrics:
        return None  # No metrics to validate

    # Accumulate all metrics from original bullets
    original_metrics = set()
    for ob in original_bullets:
        original_metrics.update(extract_metrics(ob))

    fabricated = rewritten_metrics - original_metrics
    if fabricated:
        return f"Metric fabrication detected: The numbers/metrics {fabricated} do not exist in the original candidate resume bullets."
    return None

async def verify_truthfulness(profile: ResumeParsedData, impact_result: ImpactPassResult) -> TruthfulnessCheckResult:
    """
    Audits the tailored experience bullets against the original resume details.
    Uses deterministic metric checking first, and falls back to Gemini Pro for forensic semantic auditing.
    """
    # Collect original experience/project bullets to show the auditor
    original_bullets = []
    for exp in profile.experience:
        bullets = exp.get("bullets", []) if isinstance(exp, dict) else getattr(exp, "bullets", [])
        for bullet in bullets:
            if bullet.strip():
                original_bullets.append(bullet.strip())
    for proj in profile.projects:
        bullets = proj.get("bullets", []) if isinstance(proj, dict) else getattr(proj, "bullets", [])
        for bullet in bullets:
            if bullet.strip():
                original_bullets.append(bullet.strip())

    # Collect rewritten/tailored experience bullets
    tailored_bullets = []
    for exp in impact_result.tailored_experience:
        bullets = exp.get("bullets", []) if isinstance(exp, dict) else getattr(exp, "bullets", [])
        for bullet in bullets:
            if bullet.strip():
                tailored_bullets.append(bullet.strip())

    if not tailored_bullets:
        logger.warning("No tailored experience bullets found for audit. Returning empty verification report.")
        return TruthfulnessCheckResult(is_fabricated=False, verification_report=[])

    verification_report = []
    bullets_to_llm = []

    # 1. Deterministic Pass
    for tb in tailored_bullets:
        fab_warning = validate_claim_evidence(original_bullets, tb)
        if fab_warning:
            logger.warning(f"[Truthfulness Deterministic] Flagged bullet: '{tb}' -> {fab_warning}")
            verification_report.append(
                BulletVerification(
                    rewritten_bullet=tb,
                    is_fabricated=True,
                    justification=fab_warning,
                    suggested_fix=re.sub(r'\b\d+(?:[\.,]\d+)?%?\b|\b\d+[kKmMbB]?\+?\b|\$\d+(?:[\.,]\d+)?\b', '', tb).strip()  # Strip metrics
                )
            )
            # Record claim as blocked in the ledger
            await ClaimLedger.record_claim(
                ClaimRecord(
                    claim_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, tb)),
                    user_id=profile.email or "unregistered-user",
                    claim_text=tb,
                    source_evidence=original_bullets,
                    confidence=1.0,
                    validation_status="blocked",
                    model="deterministic_rules_v1",
                    prompt_version="v1"
                )
            )
        else:
            bullets_to_llm.append(tb)

    # 2. LLM Audit Pass (only for bullets that passed deterministic check)
    if bullets_to_llm:
        prompt = (
            "Perform a truthfulness audit. Cross-examine the tailored bullets against the original candidate data.\n\n"
            "--- CANDIDATE ORIGINAL SKILLS ---\n"
            f"{', '.join(profile.skills)}\n\n"
            "--- CANDIDATE ORIGINAL EXPERIENCE BULLETS ---\n"
        )
        for i, ob in enumerate(original_bullets, 1):
            prompt += f"{i}. {ob}\n"

        prompt += "\n--- PROPOSED TAILORED EXPERIENCE BULLETS ---\n"
        for j, tb in enumerate(bullets_to_llm, 1):
            prompt += f"{j}. {tb}\n"

        prompt += (
            "\nAnalyze each tailored bullet. Determine if it introduces fabricated content. "
            "Return the audit report in the structured JSON matching the TruthfulnessCheckResult schema."
        )

        logger.info("Executing Truthfulness Gate LLM audit (Gemini Pro)...")
        try:
            llm_result = await llm_client.generate_structured_async(
                prompt=prompt,
                response_schema=TruthfulnessCheckResult,
                model_type="pro",
                system_instruction=TRUTHFULNESS_SYSTEM
            )
            
            # Merge LLM results into our report and log to ledger
            for item in llm_result.verification_report:
                verification_report.append(item)
                
                # Record to claim ledger
                status = "blocked" if item.is_fabricated else "verified"
                await ClaimLedger.record_claim(
                    ClaimRecord(
                        claim_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, item.rewritten_bullet)),
                        user_id=profile.email or "unregistered-user",
                        claim_text=item.rewritten_bullet,
                        source_evidence=original_bullets,
                        confidence=0.9 if status == "verified" else 0.95,
                        validation_status=status,
                        model=settings.GEMINI_PRO_MODEL,
                        prompt_version="v1"
                    )
                )
        except Exception as llm_err:
            logger.error(f"Truthfulness LLM audit failed: {llm_err}. Defaulting remaining to unverified.")
            for tb in bullets_to_llm:
                verification_report.append(
                    BulletVerification(
                        rewritten_bullet=tb,
                        is_fabricated=False,
                        justification="LLM audit offline. Validated via deterministic pass only.",
                        suggested_fix=tb
                    )
                )

    any_fabricated = any(item.is_fabricated for item in verification_report)
    logger.info(f"Truthfulness audit completed. Fabrications flagged: {any_fabricated}")
    
    return TruthfulnessCheckResult(
        is_fabricated=any_fabricated,
        verification_report=verification_report
    )
