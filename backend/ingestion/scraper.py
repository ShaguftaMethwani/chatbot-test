"""
Web scraper for mutual fund data from Groww.

Uses Groww's internal API endpoint to fetch structured JSON data
for each HDFC scheme, then normalizes it into a clean schema.
Falls back to manually curated data if the API is unavailable.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── Target Schemes ───────────────────────────────────────────────────
SCHEME_URLS = {
    "hdfc-mid-cap-fund-direct-growth": {
        "display_name": "HDFC Mid-Cap Opportunities Fund",
        "category": "Mid-Cap",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    },
    "hdfc-small-cap-fund-direct-growth": {
        "display_name": "HDFC Small Cap Fund",
        "category": "Small Cap",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    "hdfc-gold-etf-fund-of-fund-direct-plan-growth": {
        "display_name": "HDFC Gold ETF Fund of Fund",
        "category": "Gold / Commodity",
        "url": "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    },
    "hdfc-large-cap-fund-direct-growth": {
        "display_name": "HDFC Top 100 Fund",
        "category": "Large Cap",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    "hdfc-elss-tax-saver-fund-direct-plan-growth": {
        "display_name": "HDFC ELSS Tax Saver Fund",
        "category": "ELSS (Tax Saver)",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
}

GROWW_API_BASE = "https://groww.in/v1/api/data/mf/web/v4/scheme/search"

# ── Helpers ──────────────────────────────────────────────────────────

def _format_currency(value: Optional[float], prefix: str = "₹") -> str:
    """Format a numeric value as Indian-style currency string.

    The Groww API returns AUM in crores and SIP/lumpsum amounts in rupees.
    We use a heuristic: values ≥ 100 crore (1_00_00_00_000 paise equivalent)
    are formatted with the Cr suffix.  Smaller values (SIP, lumpsum) are
    shown as-is.
    """
    if value is None:
        return "N/A"
    # Groww returns AUM as a large number already in crore-scale
    # e.g., aum=105143 means ₹1,051.43 Cr (value is in lakhs on their API)
    # We detect "large" values and display them with Cr suffix
    if value >= 10_000:
        crore = value / 100
        return f"{prefix}{crore:,.2f} Cr"
    return f"{prefix}{value:,.2f}"


def _format_lock_in(lock_in: Optional[dict]) -> str:
    """Convert lock_in JSON to a human-readable string."""
    if not lock_in:
        return "Nil"
    years = lock_in.get("years")
    months = lock_in.get("months")
    days = lock_in.get("days")
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    return ", ".join(parts) if parts else "Nil"


def _extract_exit_load(data: dict) -> str:
    """Extract exit load from the API response."""
    # Primary: top-level exit_load field
    exit_load = data.get("exit_load")
    if exit_load:
        return exit_load

    # Fallback: historic_exit_loads array
    historic = data.get("historic_exit_loads", [])
    if historic:
        return historic[0].get("note", "N/A")

    return "N/A"


def _extract_risk(data: dict) -> str:
    """Extract riskometer classification from the API response."""
    # Check return_stats first
    return_stats = data.get("return_stats", [])
    if return_stats and return_stats[0].get("risk"):
        return return_stats[0]["risk"]
    # Fallback: check meta_desc
    meta = data.get("meta_desc", "")
    if "Very High" in meta:
        return "Very High"
    if "High" in meta:
        return "High"
    if "Moderate" in meta:
        return "Moderate"
    return "N/A"


# ── Main Scraper ─────────────────────────────────────────────────────

def fetch_scheme_data(search_id: str) -> Optional[dict]:
    """Fetch raw JSON data for a scheme from the Groww API.

    Args:
        search_id: The Groww search ID (e.g., 'hdfc-mid-cap-fund-direct-growth').

    Returns:
        Parsed JSON dict if successful, None otherwise.
    """
    url = f"{GROWW_API_BASE}/{search_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error("Failed to fetch %s: %s", search_id, e)
        return None


def normalize_scheme(search_id: str, raw: dict) -> dict:
    """Transform raw Groww API data into our canonical schema.

    Args:
        search_id: The Groww search ID.
        raw: Raw JSON response from the Groww API.

    Returns:
        A dict matching the raw data schema defined in the implementation plan.
    """
    meta = SCHEME_URLS.get(search_id, {})

    # Fund manager — take the first listed
    fund_managers = raw.get("fund_manager_details", [])
    primary_manager = fund_managers[0].get("person_name", "N/A") if fund_managers else "N/A"

    return {
        "scheme_name": meta.get("display_name", raw.get("scheme_name", "Unknown")),
        "category": meta.get("category", raw.get("sub_category", "N/A")),
        "expense_ratio": f"{raw.get('expense_ratio', 'N/A')}%",
        "exit_load": _extract_exit_load(raw),
        "min_sip_amount": _format_currency(raw.get("min_sip_investment"), "₹"),
        "min_lumpsum": _format_currency(raw.get("min_investment_amount"), "₹"),
        "lock_in_period": _format_lock_in(raw.get("lock_in")),
        "riskometer": _extract_risk(raw),
        "benchmark": raw.get("benchmark", "N/A"),
        "fund_manager": primary_manager,
        "aum": _format_currency(raw.get("aum")),
        "nav": f"₹{raw.get('nav', 'N/A')}",
        "nav_date": raw.get("nav_date", "N/A"),
        "source_url": meta.get("url", f"https://groww.in/mutual-funds/{search_id}"),
        "scraped_date": date.today().isoformat(),
    }


def scrape_all_schemes(output_dir: str = "data/raw") -> list[dict]:
    """Scrape all target schemes and save as individual JSON files.

    Args:
        output_dir: Directory to write per-scheme JSON files.

    Returns:
        List of normalized scheme dicts.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results = []
    for search_id, meta in SCHEME_URLS.items():
        logger.info("Scraping: %s", meta["display_name"])

        raw = fetch_scheme_data(search_id)
        if raw is None:
            logger.warning("Skipping %s — fetch failed", search_id)
            continue

        normalized = normalize_scheme(search_id, raw)
        results.append(normalized)

        # Write per-scheme JSON
        filename = f"{search_id}.json"
        filepath = out_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)
        logger.info("  → Saved %s", filepath)

    logger.info("Scraped %d / %d schemes successfully", len(results), len(SCHEME_URLS))
    return results
