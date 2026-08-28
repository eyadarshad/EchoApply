"""
Input sanitization utilities for user-facing text fields.

Prevents:
- Prompt injection attacks in LLM-bound text
- Path traversal in filenames
- XSS in text that might be rendered in HTML
- SQL injection (defense-in-depth alongside parameterized queries)
"""

import html
import os
import re
import logging
from typing import Any, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Patterns that indicate prompt injection attempts
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+now",
    r"act\s+as\s+if",
    r"pretend\s+you\s+are",
    r"system\s*:\s*",
    r"<\s*/?script",
    r"javascript\s*:",
    r"on(click|load|error|mouseover)\s*=",
    r"note\s+to\s+ai",
    r"instructions?\s+for\s+assistant",
    r"assistant\s+instructions?",
    r"ignore\s+the\s+above\s+instructions?",
    r"override\s+system\s+instructions?",
    r"new\s+system\s+instructions?",
    r"developer\s+instructions?",
    r"<\/DATA>",
    r"<\s*/?\s*data\s*>",
]

# Compiled for performance
_INJECTION_RE = re.compile(
    "|".join(PROMPT_INJECTION_PATTERNS),
    re.IGNORECASE
)


def sanitize_text_input(text: str, max_length: int = 50000, field_name: str = "input", raise_on_injection: bool = False) -> str:
    """
    Sanitize general text input (search queries, JD text, screening answers).
    
    - Strips leading/trailing whitespace
    - Enforces max length
    - Removes null bytes
    - Logs warnings for detected prompt injection patterns (blocks if raise_on_injection is True)
    
    Returns the cleaned text.
    """
    if not text:
        return ""
    
    # Remove null bytes (can cause issues in C-backed libraries)
    cleaned = text.replace("\x00", "")
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    # Enforce max length
    if len(cleaned) > max_length:
        logger.warning(f"[SANITIZE] {field_name} exceeded max length ({len(cleaned)} > {max_length}). Truncating.")
        cleaned = cleaned[:max_length]
    
    # Check for prompt injection patterns
    matches = _INJECTION_RE.findall(cleaned)
    if matches:
        logger.warning(
            f"[SANITIZE] Potential prompt injection detected in {field_name}: "
            f"matched patterns: {matches[:3]}"
        )
        if raise_on_injection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input contains disallowed patterns in field '{field_name}'."
            )
    
    return cleaned


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent path traversal and injection.
    
    - Extracts only the basename (no directory components)
    - Removes special characters except alphanumeric, dash, underscore, dot
    - Ensures it ends with an allowed extension
    - Limits length to 255 characters
    """
    if not filename:
        return "unnamed_file"
    
    # Extract basename only (prevents path traversal via ../../etc)
    clean = os.path.basename(filename)
    
    # Remove null bytes
    clean = clean.replace("\x00", "")
    
    # Only allow safe characters
    clean = re.sub(r"[^\w\-. ]", "_", clean)
    
    # Collapse multiple underscores/spaces
    clean = re.sub(r"[_ ]+", "_", clean).strip("_")
    
    # Limit length
    if len(clean) > 255:
        name, ext = os.path.splitext(clean)
        clean = name[:255 - len(ext)] + ext
    
    return clean or "unnamed_file"


def sanitize_search_query(query: str, max_length: int = 200) -> str:
    """
    Sanitize a job search query string.
    
    - Strips HTML tags
    - Removes excessive whitespace
    - Enforces max length
    """
    if not query:
        return ""
    
    # Strip any HTML tags
    cleaned = re.sub(r"<[^>]+>", "", query)
    
    # Normalize whitespace
    cleaned = " ".join(cleaned.split())
    
    # Enforce max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()


def sanitize_user_id(user_id: str) -> str:
    """
    Validate and sanitize a user ID string.
    Expects a UUID format. Rejects anything that doesn't look like a UUID.
    """
    if not user_id:
        return ""
    
    # Strip whitespace
    cleaned = user_id.strip()
    
    # Validate UUID format (with or without hyphens)
    uuid_pattern = re.compile(
        r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$"
    )
    
    if not uuid_pattern.match(cleaned):
        logger.warning(f"[SANITIZE] Invalid user_id format: {cleaned[:50]}")
        return ""
    
    return cleaned


def encode_html_entities(text: str) -> str:
    """Encode HTML entities to prevent XSS."""
    if not text:
        return ""
    return html.escape(text)


def sanitize_json_input(data: Any) -> Any:
    """Recursively validates and cleans nested JSON objects to prevent injection."""
    if isinstance(data, dict):
        return {k: sanitize_json_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_input(v) for v in data]
    elif isinstance(data, str):
        return sanitize_text_input(data, max_length=10000)
    return data
