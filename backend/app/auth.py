"""
Authentication & Authorization middleware for FastAPI.

Uses Supabase Auth JWT tokens for request authentication.
Every protected endpoint should use `get_current_user` as a dependency.

Flow:
1. Frontend sends `Authorization: Bearer <supabase_access_token>` header
2. This middleware decodes the JWT using Supabase's JWT secret (SUPABASE_JWT_SECRET)
3. Extracts the user_id from the token's `sub` claim
4. Returns the authenticated user context to the route handler

If SUPABASE_JWT_SECRET is not set, the middleware falls back to a development
mode that accepts any user_id passed in the header (for local testing).
"""

import os
import json
import hmac
import hashlib
import base64
import time
import logging
from typing import Optional

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.backends import default_backend
from fastapi import Depends, HTTPException, status, Request

from app.config import settings

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
if SUPABASE_JWT_SECRET.startswith("your-") or "placeholder" in SUPABASE_JWT_SECRET.lower():
    logger.warning("SUPABASE_JWT_SECRET has a placeholder value. Treating as empty (development mode).")
    SUPABASE_JWT_SECRET = ""


class AuthenticatedUser:
    """Represents an authenticated user context extracted from a JWT."""
    def __init__(self, user_id: str, email: Optional[str] = None, role: str = "user"):
        self.user_id = user_id
        self.email = email
        self.role = role


def _base64url_decode(data: str) -> bytes:
    """Decode base64url-encoded data with padding fix."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


# JWKS cache for ES256 public keys
_JWKS_CACHE = {}
_JWKS_CACHE_EXPIRY = 0.0

def _get_supabase_public_key(kid: str) -> ec.EllipticCurvePublicKey:
    """Fetch and cache public keys from Supabase JWKS endpoint for validating ES256 signatures."""
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRY
    now = time.time()
    
    # Refresh cache if empty or expired
    if not _JWKS_CACHE or now > _JWKS_CACHE_EXPIRY:
        try:
            supabase_url = settings.SUPABASE_URL or ""
            if not supabase_url:
                raise ValueError("SUPABASE_URL setting is empty.")
            jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            logger.info(f"Fetching Supabase JWKS public keys from {jwks_url}...")
            resp = httpx.get(jwks_url, timeout=5.0)
            resp.raise_for_status()
            jwks = resp.json()
            
            new_cache = {}
            for key_data in jwks.get("keys", []):
                if key_data.get("kty") == "EC" and key_data.get("crv") == "P-256":
                    # Decode public key coordinate bytes from base64url representation
                    x_bytes = _base64url_decode(key_data["x"])
                    y_bytes = _base64url_decode(key_data["y"])
                    x_val = int.from_bytes(x_bytes, byteorder="big")
                    y_val = int.from_bytes(y_bytes, byteorder="big")
                    
                    public_numbers = ec.EllipticCurvePublicNumbers(
                        x_val, y_val, ec.SECP256R1()
                    )
                    pub_key = public_numbers.public_key(default_backend())
                    new_cache[key_data["kid"]] = pub_key
                    
            _JWKS_CACHE = new_cache
            _JWKS_CACHE_EXPIRY = now + 3600  # Cache for 1 hour
            logger.info("Successfully populated Supabase JWKS public key cache.")
        except Exception as e:
            logger.error(f"Failed to fetch or parse Supabase JWKS keys: {e}")
            _JWKS_CACHE_EXPIRY = now + 60  # Retry in 1 minute on failure
            
    if kid in _JWKS_CACHE:
        return _JWKS_CACHE[kid]
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unknown Key ID (kid): '{kid}' for Supabase ES256 validation."
    )

def _verify_hs256(token: str, secret: str) -> dict:
    """
    Manually verify JWT token signatures.
    Supports both standard HS256 (symmetric) and new Supabase ES256 (asymmetric) algorithms.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: expected 3 parts"
        )

    header_b64, payload_b64, signature_b64 = parts

    # Parse header
    try:
        header = json.loads(_base64url_decode(header_b64))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header encoding"
        )

    alg = header.get("alg")
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    
    if alg == "HS256":
        # Symmetric HMAC-SHA256 signature verification
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Symmetric secret not configured for HS256 token verification."
            )
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        
        try:
            actual_sig = _base64url_decode(signature_b64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature base64url encoding"
            )
            
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature"
            )
            
    elif alg == "ES256":
        # Asymmetric Elliptic Curve (ECDSA SECP256R1) signature verification
        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ES256 token header missing 'kid' claim."
            )
        
        # Retrieve the cached public key matching the key ID
        pub_key = _get_supabase_public_key(kid)
        
        try:
            sig_bytes = _base64url_decode(signature_b64)
            if len(sig_bytes) != 64:
                raise ValueError("ES256 signature must be exactly 64 bytes")
            r = int.from_bytes(sig_bytes[:32], byteorder="big")
            s = int.from_bytes(sig_bytes[32:], byteorder="big")
            der_signature = encode_dss_signature(r, s)
        except Exception as sig_err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid signature encoding format: {sig_err}"
            )
            
        try:
            pub_key.verify(der_signature, signing_input, ec.ECDSA(hashes.SHA256()))
        except Exception as verify_err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed for ES256: {verify_err}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported token algorithm: '{alg}'. Expected HS256 or ES256."
        )

    # Decode and validate payload
    try:
        payload = json.loads(_base64url_decode(payload_b64))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload JSON encoding"
        )

    # Verify expiration (allow 60 seconds clock drift grace window)
    exp = payload.get("exp")
    if exp is not None:
        if time.time() > (exp + 60):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Token has expired", "token_expired": True}
            )

    # Verify audience
    aud = payload.get("aud")
    if aud not in ("authenticated", "anon"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token audience: {aud}"
        )

    return payload


async def get_current_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the authenticated user
    from the request's Authorization header.
    
    Usage in routes:
        @app.get("/api/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    
    In development mode (no SUPABASE_JWT_SECRET set), accepts:
        - Authorization: Bearer <any_token> — extracts 'sub' claim without verification
        - X-Dev-User-Id: <user_id> — directly uses the provided user_id
    """
    auth_header = request.headers.get("Authorization", "")
    dev_user_id = request.headers.get("X-Dev-User-Id", "")

    # --- Production mode: JWT verification ---
    if SUPABASE_JWT_SECRET:
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header. Expected: Bearer <token>"
            )
        
        token = auth_header.removeprefix("Bearer ").strip()
        payload = _verify_hs256(token, SUPABASE_JWT_SECRET)
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' (user ID) claim"
            )
        
        return AuthenticatedUser(
            user_id=user_id,
            email=payload.get("email"),
            role=payload.get("role", "user")
        )

    # --- Development mode: No JWT secret configured ---
    # PRODUCTION LOCKDOWN: Refuse dev bypass in production
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. SUPABASE_JWT_SECRET must be configured in production."
        )
    
    logger.warning("AUTH: Running in DEVELOPMENT mode (no SUPABASE_JWT_SECRET). Authentication is bypassed.")

    # Try to extract from a Bearer token without verification (for Supabase client testing)
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            parts = token.split(".")
            if len(parts) == 3:
                payload = json.loads(_base64url_decode(parts[1]))
                user_id = payload.get("sub")
                if user_id:
                    return AuthenticatedUser(
                        user_id=user_id,
                        email=payload.get("email"),
                        role=payload.get("role", "user")
                    )
        except Exception:
            pass
    
    # Fall back to dev header
    if dev_user_id:
        return AuthenticatedUser(user_id=dev_user_id, email="dev@localhost", role="user")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No authentication provided. Send Authorization: Bearer <token> or X-Dev-User-Id header."
    )


async def get_optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """
    Same as get_current_user but returns None instead of raising 401.
    Use for endpoints that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
