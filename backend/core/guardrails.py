"""
Pre-processing guardrails to detect and refuse advisory queries, PII, and prompt injection.
"""
import re
import logging
from typing import Tuple, Optional

from backend.config.prompts import (
    REFUSAL_ADVISORY,
    REFUSAL_PII,
)

# We use a generic refusal for injection
REFUSAL_INJECTION = "I cannot process this request as it violates my safety guidelines."

logger = logging.getLogger(__name__)

ADVISORY_PATTERNS = [
    r"\bshould\s+i\b",
    r"\brecommend\b",
    r"\bwhich\s+(is|fund|one)\s+(is\s+)?(better|best)\b",
    r"\bbest\s+(fund|scheme|option|investment)\b",
    r"\binvest\s+in\b",
    r"\bgood\s+(investment|fund|option|choice)\b",
    r"\bworth\s+(investing|buying)\b",
    r"\bcompare\b.*\b(performance|returns)\b",
    r"\breturn\s+calculation\b",
    r"\bhow\s+much\s+(will|can)\s+i\s+(earn|get|make)\b",
    r"\bpredict\b",
    r"\bforecast\b",
    # Additional patterns from edge-cases doc (E2.8–E2.13)
    r"\bsafe\s+bet\b",
    r"\btoo\s+(high|low|much|expensive)\b",
    r"\byour\s+(pick|choice|opinion)\b",
    r"\brate\s+(this|it|the)\b",
    r"\bwhat\s+would\s+you\s+do\b",
    r"\bwill\s+give\s+good\s+returns\b",
]

PII_PATTERNS = {
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "phone": r"\b[6-9]\d{9}\b",
    "email": r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now",
    r"forget\s+(everything|your\s+instructions)",
    r"new\s+instructions",
    r"system\s*prompt",
    r"act\s+as\s+a",
    r"pretend\s+(to\s+be|you\s+are)",
]


def check_pii(query: str) -> bool:
    """Returns True if PII is detected."""
    # We do not log the query if it has PII
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


def check_injection(query: str) -> bool:
    """Returns True if prompt injection is detected."""
    lower_query = query.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_query):
            logger.warning(f"Prompt injection detected using pattern: {pattern}")
            return True
    return False


def check_advisory(query: str) -> bool:
    """Returns True if advisory intent is detected."""
    lower_query = query.lower()
    
    # Edge case handler: allow specific safe informational phrasing that
    # contains advisory keywords but is NOT advisory in intent.
    safe_phrases = [
        "should i check",
        "should i look",
        "how do i invest",
        "how to invest",
        "can i invest",
    ]
    for phrase in safe_phrases:
        if phrase in lower_query:
            return False
        
    for pattern in ADVISORY_PATTERNS:
        if re.search(pattern, lower_query):
            logger.info(f"Advisory intent detected using pattern: {pattern}")
            return True
    return False


def check_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Runs all safety checks in order.
    Returns (is_allowed, refusal_response).
    If is_allowed is True, refusal_response is None.
    """
    # 1. PII Detection (do not log input if PII found)
    if check_pii(query):
        return False, REFUSAL_PII

    # 2. Prompt Injection
    if check_injection(query):
        return False, REFUSAL_INJECTION

    # 3. Advisory Intent
    if check_advisory(query):
        return False, REFUSAL_ADVISORY

    # 4. Allowed
    return True, None
