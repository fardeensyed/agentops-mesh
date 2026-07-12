import re
import json
from typing import Any, Dict
from sqlalchemy.orm import Session
from .models import AgentConfig, APIKey

# ── PII detection patterns ───────────────────────────────────────────────────
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
    """Walks span attributes and redacts PII from any string values."""
    redacted = {}
    for key, value in attributes.items():
        if isinstance(value, str):
            redacted[key] = redact_text(value)
        elif isinstance(value, dict):
            redacted[key] = redact_attributes(value)
        else:
            redacted[key] = value
    return redacted


# ── Spend limit checking ─────────────────────────────────────────────────────

def get_project_spend_limit(db: Session, project_id) -> float | None:
    """Returns the spend limit for a project, or None if unlimited."""
    config = db.query(AgentConfig).filter(
        AgentConfig.project_id == project_id
    ).first()
    return config.spend_limit_usd if config else None


def check_spend_limit(db: Session, project_id, clickhouse_client) -> Dict[str, Any]:
    """
    Sums today's cost for this project from ClickHouse, compares against
    the configured limit in PostgreSQL.
    """
    limit = get_project_spend_limit(db, project_id)
    if limit is None:
        return {"blocked": False, "spent": 0, "limit": None}

    result = clickhouse_client.query("""
        SELECT sum(JSONExtractFloat(attributes, 'cost_usd')) as spent
        FROM spans
        WHERE toDate(start_time) = today()
    """)
    spent = result.result_rows[0][0] or 0.0

    return {
        "blocked": spent >= limit,
        "spent": round(spent, 4),
        "limit": limit,
    }