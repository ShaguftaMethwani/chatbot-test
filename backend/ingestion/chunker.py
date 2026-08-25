"""
Document chunker for mutual fund scheme data.

Converts normalized scheme JSON into semantic text chunks suitable
for embedding and retrieval. Each chunk is a self-contained sentence
with attached metadata for source attribution.

Produces two types of chunks per scheme:
1. **Field-level chunks** — one per data field (expense ratio, exit load, etc.)
   for precise single-field retrieval.
2. **Composite chunks** — grouped overviews (investment details, fund profile,
   entry/exit terms) for broader queries and richer embeddings.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _make_chunk(
    text: str,
    scheme_name: str,
    field_type: str,
    source_url: str,
    scraped_date: str,
) -> dict:
    """Create a chunk dict with text and metadata.

    Args:
        text: The human-readable text content of the chunk.
        scheme_name: Canonical scheme name.
        field_type: Semantic label (e.g., 'expense_ratio', 'exit_load').
        source_url: URL where the data was sourced from.
        scraped_date: ISO-format date when the data was scraped.

    Returns:
        A dict with 'text' and 'metadata' keys.
    """
    return {
        "text": text,
        "metadata": {
            "scheme_name": scheme_name,
            "field_type": field_type,
            "source_url": source_url,
            "scraped_date": scraped_date,
        },
    }


def _safe(scheme: dict, key: str) -> Optional[str]:
    """Return the value for *key* if present and not a placeholder."""
    val = scheme.get(key)
    if not val or val in ("N/A", "₹N/A"):
        return None
    return val


def chunk_scheme(scheme: dict) -> list[dict]:
    """Convert a single normalized scheme dict into semantic chunks.

    Produces **field-level** chunks (one per data attribute) as well as
    **composite** chunks that group related fields together.  The composite
    chunks provide richer context for broader queries while the field-level
    chunks give precise retrieval for specific questions.

    Args:
        scheme: A normalized scheme dict (output of scraper.normalize_scheme).

    Returns:
        List of chunk dicts, each with 'text' and 'metadata'.
    """
    name = scheme["scheme_name"]
    url = scheme["source_url"]
    date = scheme["scraped_date"]

    chunks = []

    # ── Field-Level Chunks ───────────────────────────────────────

    # Expense Ratio
    if _safe(scheme, "expense_ratio"):
        chunks.append(_make_chunk(
            f"{name} has an expense ratio of {scheme['expense_ratio']} (Direct Plan).",
            name, "expense_ratio", url, date,
        ))

    # Exit Load
    if _safe(scheme, "exit_load"):
        exit_text = scheme["exit_load"]
        # Avoid duplication like "exit load: Exit load of 1%..."
        if exit_text.lower().startswith("exit load"):
            chunks.append(_make_chunk(
                f"{name}: {exit_text}.",
                name, "exit_load", url, date,
            ))
        else:
            chunks.append(_make_chunk(
                f"{name} exit load: {exit_text}.",
                name, "exit_load", url, date,
            ))

    # Minimum SIP Amount
    if _safe(scheme, "min_sip_amount"):
        chunks.append(_make_chunk(
            f"{name} minimum SIP amount is {scheme['min_sip_amount']}.",
            name, "min_sip_amount", url, date,
        ))

    # Minimum Lumpsum
    if _safe(scheme, "min_lumpsum"):
        chunks.append(_make_chunk(
            f"{name} minimum lumpsum investment is {scheme['min_lumpsum']}.",
            name, "min_lumpsum", url, date,
        ))

    # Lock-in Period
    if scheme.get("lock_in_period"):
        chunks.append(_make_chunk(
            f"{name} lock-in period: {scheme['lock_in_period']}.",
            name, "lock_in_period", url, date,
        ))

    # Riskometer
    if _safe(scheme, "riskometer"):
        chunks.append(_make_chunk(
            f"{name} riskometer classification: {scheme['riskometer']}.",
            name, "riskometer", url, date,
        ))

    # Benchmark
    if _safe(scheme, "benchmark"):
        chunks.append(_make_chunk(
            f"{name} benchmark index: {scheme['benchmark']}.",
            name, "benchmark", url, date,
        ))

    # Fund Manager + AUM
    if _safe(scheme, "fund_manager"):
        aum_part = f" AUM: {scheme['aum']}." if _safe(scheme, "aum") else ""
        chunks.append(_make_chunk(
            f"{name} fund manager: {scheme['fund_manager']}.{aum_part}",
            name, "fund_manager", url, date,
        ))

    # NAV
    if _safe(scheme, "nav"):
        nav_date_part = f" (as of {scheme['nav_date']})" if scheme.get("nav_date") else ""
        chunks.append(_make_chunk(
            f"{name} NAV: {scheme['nav']}{nav_date_part}.",
            name, "nav", url, date,
        ))

    # Category
    if _safe(scheme, "category"):
        chunks.append(_make_chunk(
            f"{name} is a {scheme['category']} fund.",
            name, "category", url, date,
        ))

    # ── Composite Chunks ─────────────────────────────────────────
    # These group related fields for richer embeddings and broader queries.

    # Composite 1: Investment Details
    inv_parts = [f"{name} is a {scheme.get('category', 'N/A')} fund."]
    if _safe(scheme, "expense_ratio"):
        inv_parts.append(f"Expense ratio: {scheme['expense_ratio']} (Direct Plan).")
    if _safe(scheme, "min_sip_amount"):
        inv_parts.append(f"Minimum SIP: {scheme['min_sip_amount']}.")
    if _safe(scheme, "min_lumpsum"):
        inv_parts.append(f"Minimum lumpsum: {scheme['min_lumpsum']}.")
    if scheme.get("lock_in_period"):
        inv_parts.append(f"Lock-in period: {scheme['lock_in_period']}.")

    if len(inv_parts) > 1:
        chunks.append(_make_chunk(
            " ".join(inv_parts),
            name, "investment_details", url, date,
        ))

    # Composite 2: Fund Profile
    prof_parts = [f"{name} fund profile."]
    if _safe(scheme, "benchmark"):
        prof_parts.append(f"Benchmark index: {scheme['benchmark']}.")
    if _safe(scheme, "fund_manager"):
        prof_parts.append(f"Fund manager: {scheme['fund_manager']}.")
    if _safe(scheme, "aum"):
        prof_parts.append(f"AUM: {scheme['aum']}.")
    if _safe(scheme, "nav"):
        nav_date_part = f" (as of {scheme.get('nav_date', '')})" if scheme.get("nav_date") else ""
        prof_parts.append(f"NAV: {scheme['nav']}{nav_date_part}.")
    if _safe(scheme, "riskometer"):
        prof_parts.append(f"Riskometer: {scheme['riskometer']}.")

    if len(prof_parts) > 1:
        chunks.append(_make_chunk(
            " ".join(prof_parts),
            name, "fund_profile", url, date,
        ))

    # Composite 3: Entry/Exit Terms
    terms_parts = [f"{name} entry and exit terms."]
    if _safe(scheme, "exit_load"):
        terms_parts.append(f"Exit load: {scheme['exit_load']}.")
    if scheme.get("lock_in_period"):
        terms_parts.append(f"Lock-in period: {scheme['lock_in_period']}.")
    if _safe(scheme, "min_sip_amount"):
        terms_parts.append(f"Minimum SIP: {scheme['min_sip_amount']}.")
    if _safe(scheme, "min_lumpsum"):
        terms_parts.append(f"Minimum lumpsum: {scheme['min_lumpsum']}.")

    if len(terms_parts) > 1:
        chunks.append(_make_chunk(
            " ".join(terms_parts),
            name, "entry_exit_terms", url, date,
        ))

    logger.debug("Created %d chunks for %s", len(chunks), name)
    return chunks


def chunk_help_article(article: dict) -> list[dict]:
    """Chunk a help article into smaller semantic paragraphs."""
    title = article["title"]
    url = article["source_url"]
    date = article["scraped_date"]
    content = article["content"]
    
    chunks = []
    # Split by double newline to get logical paragraphs
    paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
    
    # If a paragraph is too long, the embedding model handles truncation, 
    # but breaking by paragraph is usually safe enough for help articles.
    for i, para in enumerate(paragraphs):
        # Prefix the chunk with the title for context
        chunk_text = f"{title}\n{para}"
        chunks.append(_make_chunk(
            chunk_text,
            title, "help_content", url, date,
        ))
        
    logger.debug("Created %d chunks for help article: %s", len(chunks), title)
    return chunks


def chunk_all_documents(docs: list[dict]) -> list[dict]:
    """Chunk all normalized documents (schemes + help articles).

    Args:
        docs: List of normalized dicts.

    Returns:
        Flat list of all chunks across all documents.
    """
    all_chunks = []
    for doc in docs:
        if doc.get("type") == "help_article":
            all_chunks.extend(chunk_help_article(doc))
        else:
            # Fallback for existing scheme format
            all_chunks.extend(chunk_scheme(doc))
            
    logger.info("Total chunks created: %d (from %d documents)", len(all_chunks), len(docs))
    return all_chunks
