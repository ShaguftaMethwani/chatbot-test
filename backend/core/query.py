"""
Query preprocessor to clean and normalize user queries.
"""
import re
from backend.config.prompts import SCHEME_ALIASES

# Abbreviation expansions — appended to the query to boost retrieval,
# rather than replacing the original term (which would mismatch chunk text).
ABBREVIATION_EXPANSIONS = {
    "nav": "net asset value",
    "aum": "assets under management",
    "sip": "systematic investment plan",
    "elss": "equity linked savings scheme",
    "ter": "total expense ratio",
}

# Query enhancement synonyms — appended when a key term is detected
# to improve embedding similarity with chunk text.
QUERY_ENHANCEMENTS = {
    "expense ratio": "TER total expense annual charge",
    "exit load": "redemption fee penalty early withdrawal",
    "lock in": "lock-in period holding mandatory",
    "lumpsum": "lump sum one time investment minimum",
    "riskometer": "risk level classification category",
    "benchmark": "benchmark index tracking",
    "fund manager": "fund manager portfolio manager",
}


def preprocess_query(query: str) -> str:
    """
    Normalizes text, expands abbreviations additively, resolves informal
    scheme names, and enhances query with synonyms for better retrieval.
    """
    normalized = query.lower().strip()

    # Step 1: Resolve scheme aliases — replace informal names with canonical names
    for alias, canonical in SCHEME_ALIASES.items():
        if alias in normalized:
            # Replace the alias with the lowercased canonical name so the
            # rest of the query stays consistently lowercased.
            normalized = normalized.replace(alias, canonical.lower())
            break  # Only match one alias to avoid double-replacement

    # Step 2: Additive abbreviation expansion — append expansions for known
    # abbreviations without removing the original term.
    tokens = normalized.split()
    expansions = []
    for token in tokens:
        if token in ABBREVIATION_EXPANSIONS:
            expansions.append(ABBREVIATION_EXPANSIONS[token])
    if expansions:
        normalized = normalized + " " + " ".join(expansions)

    # Step 3: Query enhancement — append synonyms when key terms are detected
    enhancements = []
    for term, synonyms in QUERY_ENHANCEMENTS.items():
        if term in normalized:
            enhancements.append(synonyms)
    if enhancements:
        normalized = normalized + " " + " ".join(enhancements)

    return normalized
