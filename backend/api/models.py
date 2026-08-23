"""
Pydantic models for the FastAPI API layer.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    source: Optional[str] = None
    last_updated: Optional[str] = None
    refused: bool = False


class HealthResponse(BaseModel):
    status: str
    vector_store_count: int
    last_ingestion: Optional[str] = None
