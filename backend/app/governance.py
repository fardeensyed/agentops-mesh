import re
import json
from typing import Any, Dict

# ── PII detection patterns ───────────────────────────────────────────────────
# Each pattern finds one type of sensitive data in text
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
}


def redact_text(text: str) -> str:
    """Replaces any detected PII in a string with [REDACTED_<type>]."""
    if not isinstance(text, str):
        return text
    for pii_type, pattern in PII_PATTERNS.items():
        text = pattern.sub(f"[REDACTED_{pii_type.upper()}]", text)
    return text


def redact_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Walks through span attributes and redacts PII from any string values.
    Numbers, booleans, and non-PII strings pass through unchanged.
    """
    redacted = {}
    for key, value in attributes.items():
        if isinstance(value, str):
            redacted[key] = redact_text(value)
        elif isinstance(value, dict):
            redacted[key] = redact_attributes(value)  # recurse into nested dicts
        else:
            redacted[key] = value  # numbers, booleans stay as-is
    return redacted