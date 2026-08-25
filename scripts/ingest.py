#!/usr/bin/env python3
"""
Ingestion orchestration script.
Runs the pipeline: scrape -> chunk -> embed -> store.
"""
import logging
import os
import sys
from dotenv import load_dotenv

# Add project root to Python path so 'backend' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env file from backend/.env if running from root
load_dotenv("backend/.env")

from backend.ingestion.scraper import scrape_all_schemes, scrape_help_pages
from backend.ingestion.chunker import chunk_all_documents
from backend.ingestion.embedder import embed_and_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("Starting ingestion pipeline...")
    
    # 1. Scrape
    logger.info("--- Step 1: Scrape ---")
    schemes = scrape_all_schemes(output_dir="backend/data/raw")
    help_articles = scrape_help_pages(output_dir="backend/data/raw")
    
    all_docs = schemes + help_articles
    if not all_docs:
        logger.error("No data scraped (and no fallbacks). Aborting.")
        sys.exit(1)
        
    # 2. Chunk
    logger.info("--- Step 2: Chunk ---")
    chunks = chunk_all_documents(all_docs)
    
    if not chunks:
        logger.error("No chunks generated. Exiting.")
        sys.exit(1)
        
    # 3. Embed & Store
    logger.info("--- Step 3: Embed & Store ---")
    embed_and_store(chunks)

    # 4. Record ingestion timestamp
    from datetime import datetime, timezone
    from backend.vectorstore.store import get_store
    timestamp = datetime.now(timezone.utc).isoformat()
    get_store().set_last_ingestion(timestamp)
    logger.info("Recorded ingestion timestamp: %s", timestamp)
    
    logger.info("Ingestion pipeline completed successfully.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
