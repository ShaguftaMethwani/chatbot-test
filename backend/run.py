#!/usr/bin/env python3
"""
Uvicorn startup script for the FastAPI backend.
"""
import uvicorn
import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Explicitly load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"Starting server at http://{settings.host}:{settings.port}")
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
