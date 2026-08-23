#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Railway startup script
# Runs ingestion pipeline (scrape → chunk → embed → store)
# then starts the FastAPI server.
#
# Railway injects $PORT automatically — never hardcode it.
# ──────────────────────────────────────────────────────────────
set -e  # Exit immediately on any error

echo "=========================================="
echo " HDFC Mutual Fund Assistant — Railway Start"
echo "=========================================="

# Step 1: Rebuild ChromaDB from latest data.
# Railway's filesystem is ephemeral, so data/chroma_db/ is always
# empty on startup. This step scrapes Groww (or falls back to cached
# raw JSON) and populates the vector store before traffic is served.
echo ""
echo "=== Step 1: Running ingestion pipeline ==="
python scripts/ingest.py

echo ""
echo "=== Step 2: Starting FastAPI server on port ${PORT:-8000} ==="
exec uvicorn backend.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
