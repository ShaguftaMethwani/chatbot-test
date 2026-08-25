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

# ── Target Help Pages ──────────────────────────────────────────────────
HELP_URLS = {
    "help-download-statement": "https://groww.in/help/mutual-funds/statements/how-to-download-mutual-fund-statement",
    "help-download-capital-gains": "https://groww.in/help/mutual-funds/taxation/how-to-download-capital-gains-statement",
    "help-elss-tax-proof": "https://groww.in/help/mutual-funds/taxation/elss-tax-saving-investment-proof",
    "help-tax-calculation": "https://groww.in/help/mutual-funds/taxation/how-is-tax-calculated-on-mutual-funds",
    "help-cas-statement": "https://groww.in/help/mutual-funds/statements/what-is-a-consolidated-account-statement-cas",
    "help-expense-ratio": "https://groww.in/help/mutual-funds/general/what-is-expense-ratio",
    "help-exit-load": "https://groww.in/help/mutual-funds/general/what-is-exit-load",
    "help-nav": "https://groww.in/help/mutual-funds/general/what-is-nav-net-asset-value",
    "help-riskometer": "https://groww.in/help/mutual-funds/general/what-is-a-riskometer",
    "help-min-sip": "https://groww.in/help/mutual-funds/sips/what-is-the-minimum-sip-amount"
}

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


def scrape_all_schemes(output_dir: str = "backend/data/raw") -> list[dict]:
    """Scrape all target schemes and save as individual JSON files.

    If the Groww API is unavailable for a scheme (e.g. during a Railway cold
    start or network outage), the scraper falls back to the last committed JSON
    file in *output_dir* rather than skipping the scheme entirely.

    Args:
        output_dir: Directory to write per-scheme JSON files.

    Returns:
        List of normalized scheme dicts (live + fallback combined).
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results = []
    for search_id, meta in SCHEME_URLS.items():
        logger.info("Scraping: %s", meta["display_name"])

        raw = fetch_scheme_data(search_id)

        if raw is None:
            # --- Fallback: load last committed JSON if available ---
            fallback_path = out_path / f"{search_id}.json"
            if fallback_path.exists():
                try:
                    with open(fallback_path, encoding="utf-8") as f:
                        normalized = json.load(f)
                    logger.warning(
                        "Groww API unavailable — using cached fallback data for %s",
                        search_id,
                    )
                    results.append(normalized)
                except Exception as e:
                    logger.error("Failed to load fallback JSON for %s: %s", search_id, e)
            else:
                logger.warning(
                    "Skipping %s — fetch failed and no fallback data available",
                    search_id,
                )
            continue

        normalized = normalize_scheme(search_id, raw)
        results.append(normalized)

        # Write per-scheme JSON (also updates the fallback for next time)
        filename = f"{search_id}.json"
        filepath = out_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)
        logger.info("  → Saved %s", filepath)

    logger.info("Scraped %d / %d schemes successfully", len(results), len(SCHEME_URLS))
    return results


def scrape_help_pages(output_dir: str = "backend/data/raw") -> list[dict]:
    """Scrape Mutual Fund educational/help articles from Groww.
    
    Extracts text using BeautifulSoup. Falls back to cached JSON if network fails.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 is required for scraping help pages. Install it with `pip install beautifulsoup4`")
        return []

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    results = []
    for search_id, url in HELP_URLS.items():
        logger.info("Scraping Help Article: %s", search_id)
        
        fallback_path = out_path / f"{search_id}.json"
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # The title is usually in an h1
            title_el = soup.find("h1")
            title = title_el.get_text(strip=True) if title_el else search_id.replace("help-", "").replace("-", " ").title()
            
            # Extract paragraphs and list items from the main content area
            # We target the main layout to avoid header/footer noise if possible, or just grab all p/li
            content_div = soup.find("div", class_="qap761TextAnswer") or soup.find("div", class_="answerWrapper") or soup.find("main")
            
            if content_div:
                elements = content_div.find_all(['p', 'li', 'h2', 'h3'])
            else:
                # Fallback: grab all standard text elements
                elements = soup.find_all(['p', 'li', 'h2', 'h3'])
                
            text_blocks = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
            
            # Filter out obvious UI junk like "Was the answer helpful?" or footer links
            clean_blocks = [
                text for text in text_blocks 
                if not text.startswith("Was the answer helpful") 
                and not text.startswith("Download the App")
                and len(text) > 20  # Ignore tiny UI buttons
            ]
            
            article_text = "\n\n".join(clean_blocks)
            
            normalized = {
                "type": "help_article",
                "id": search_id,
                "title": title,
                "content": article_text,
                "source_url": url,
                "scraped_date": date.today().isoformat(),
            }
            
            # Save to disk
            with open(fallback_path, "w", encoding="utf-8") as f:
                json.dump(normalized, f, indent=2, ensure_ascii=False)
            logger.info("  → Saved %s", fallback_path)
            results.append(normalized)
            
        except Exception as e:
            logger.error("Failed to scrape %s: %s", url, e)
            if fallback_path.exists():
                try:
                    with open(fallback_path, encoding="utf-8") as f:
                        results.append(json.load(f))
                    logger.warning("  → Using cached fallback data for %s", search_id)
                except Exception as inner_e:
                    logger.error("  → Failed to load fallback JSON: %s", inner_e)
            else:
                logger.warning("  → Skipping %s — no fallback available", search_id)
                
    logger.info("Scraped %d / %d help pages successfully", len(results), len(HELP_URLS))
    return results
