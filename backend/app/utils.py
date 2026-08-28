import os
import json
import base64
import uuid
import hashlib
import logging
from typing import List, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

def clean_uuid(user_id: str) -> str:
    """Helper to convert any transient user_id into a valid UUID string format."""
    if not user_id:
        return str(uuid.uuid4())
    try:
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))

# Derive encryption key from env var — NEVER hardcode secrets in source
_enc_secret = settings.ENCRYPTION_SECRET
if not _enc_secret:
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError("ENCRYPTION_SECRET must be set in production!")
    _enc_secret = "dev-fallback-key-change-me-in-production"

ENCRYPTION_KEY_RAW = hashlib.sha256(_enc_secret.encode("utf-8")).digest()

_enc_secret_old = os.getenv("ENCRYPTION_SECRET_OLD", "")
ENCRYPTION_KEY_RAW_OLD = hashlib.sha256(_enc_secret_old.encode("utf-8")).digest() if _enc_secret_old else None

def encrypt_value(plain_text: str) -> str:
    aesgcm = AESGCM(ENCRYPTION_KEY_RAW)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")

def decrypt_value(cipher_text: str) -> str:
    try:
        data = base64.b64decode(cipher_text.encode("utf-8"))
        if len(data) < 13:  # Nonce (12 bytes) + tag (16 bytes) means it must be > 12 bytes
            logger.error("Ciphertext too short to validate nonce length.")
            return ""
        nonce = data[:12]
        ct = data[12:]
        
        try:
            aesgcm = AESGCM(ENCRYPTION_KEY_RAW)
            return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
        except Exception:
            if ENCRYPTION_KEY_RAW_OLD:
                logger.info("Primary decryption failed. Attempting old key fallback...")
                aesgcm_old = AESGCM(ENCRYPTION_KEY_RAW_OLD)
                return aesgcm_old.decrypt(nonce, ct, None).decode("utf-8")
            raise
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""

async def get_platform_cookies(user_id: str, platform: str) -> List[Dict[str, Any]]:
    """Retrieve and decrypt session cookies for a platform, with local fallback support."""
    encrypted_str = None
    # 1. Try DB first
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT cookies_encrypted FROM platform_credentials WHERE user_id = %s AND platform = %s;",
                        (clean_uuid(user_id), platform)
                    )
                    row = await cur.fetchone()
                    if row:
                        encrypted_str = row[0]
    except Exception as e:
        logger.warning(f"DB cookie lookup failed: {e}")
        
    # 2. Try Local fallback if DB is unreachable
    if not encrypted_str:
        file_path = os.path.join(settings.DATA_DIR, "credentials", f"{clean_uuid(user_id)}_{platform}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    encrypted_str = data.get("encrypted_cookies")
            except Exception as e:
                logger.error(f"Failed to read local cookie fallback: {e}")
                
    if encrypted_str:
        plain_str = decrypt_value(encrypted_str)
        if plain_str:
            try:
                return json.loads(plain_str)
            except Exception:
                pass
    return []
