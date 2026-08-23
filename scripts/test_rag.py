#!/usr/bin/env python3
"""
Verification script for the RAG Core & LLM Integration (Phase 3).
"""
import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv("backend/.env")

from backend.core.generator import get_generator

def test_queries():
    generator = get_generator()
    
    queries = [
        "What is the expense ratio of HDFC Mid Cap?",
        "What is the minimum SIP amount for the Small Cap fund?",
        "Should I invest my life savings in the top 100 fund?",
        "What is the weather in Mumbai?"
    ]
    
    for q in queries:
        print(f"\n[{'='*50}]")
        print(f"Query: {q}")
        print(f"[{'='*50}]")
        try:
            response = generator.generate_response(q)
            print(f"Answer: {response['answer']}")
            print(f"Source: {response['source']}")
            print(f"Last Updated: {response['last_updated']}")
            print(f"Refused: {response['refused']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_queries()
