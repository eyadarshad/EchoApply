import os
import json
import time
import logging
from typing import List, Optional
from pydantic import BaseModel
from app.config import settings
from app.database import get_db
from app.utils import clean_uuid

logger = logging.getLogger(__name__)

class ClaimRecord(BaseModel):
    claim_id: str
    application_id: Optional[str] = None
    user_id: str
    claim_text: str
    source_evidence: List[str]
    confidence: float
    validation_status: str  # "verified", "unverified", "blocked"
    model: str
    prompt_version: str

_LAST_DB_FAILURE_TIME = 0.0
_DB_FAILURE_COOLDOWN = 15.0  # seconds to skip DB retry after a connection timeout

class ClaimLedger:
    @staticmethod
    async def record_claim(record: ClaimRecord):
        """Records a claim to the database or fallback local ledger."""
        global _LAST_DB_FAILURE_TIME
        logger.info(f"[ClaimLedger] Recording claim {record.claim_id} for user {record.user_id}...")
        
        db_saved = False
        now = time.time()
        
        # Only attempt DB insert if not in cooldown from a recent connection failure
        if now - _LAST_DB_FAILURE_TIME > _DB_FAILURE_COOLDOWN:
            try:
                async with get_db() as conn:
                    if conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """
                                INSERT INTO claim_ledger (
                                    claim_id, application_id, user_id, claim_text, source_evidence, confidence, validation_status, model, prompt_version
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (claim_id) DO UPDATE SET
                                    validation_status = EXCLUDED.validation_status,
                                    confidence = EXCLUDED.confidence;
                                """,
                                (
                                    record.claim_id,
                                    clean_uuid(record.application_id) if record.application_id else None,
                                    clean_uuid(record.user_id),
                                    record.claim_text,
                                    record.source_evidence,
                                    record.confidence,
                                    record.validation_status,
                                    record.model,
                                    record.prompt_version
                                )
                            )
                            await conn.commit()
                            db_saved = True
            except Exception as e:
                _LAST_DB_FAILURE_TIME = time.time()
                logger.warning(f"[ClaimLedger] Database save failed: {e}. Falling back to local file ledger.")

        if not db_saved:
            # Local fallback file
            fallback_dir = os.path.join(settings.DATA_DIR, "ledger")
            os.makedirs(fallback_dir, exist_ok=True)
            ledger_file = os.path.join(fallback_dir, "claim_ledger.json")
            
            try:
                ledger_data = []
                if os.path.exists(ledger_file):
                    with open(ledger_file, "r", encoding="utf-8") as f:
                        ledger_data = json.load(f)
                
                # Check for existing claim_id to update
                existing_idx = next((i for i, r in enumerate(ledger_data) if r.get("claim_id") == record.claim_id), None)
                if existing_idx is not None:
                    ledger_data[existing_idx] = record.model_dump()
                else:
                    ledger_data.append(record.model_dump())
                    
                with open(ledger_file, "w", encoding="utf-8") as f:
                    json.dump(ledger_data, f, indent=2)
                logger.info(f"[ClaimLedger] Local save successful for claim {record.claim_id}.")
            except Exception as file_err:
                logger.error(f"[ClaimLedger] Failed to write fallback file: {file_err}")
