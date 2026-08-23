"""
FastAPI routes for chat and health endpoints.
"""
import logging

from fastapi import APIRouter, HTTPException
from backend.api.models import ChatRequest, ChatResponse, HealthResponse
from backend.core.generator import get_generator
from backend.vectorstore.store import get_store

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Receives user query, runs guardrails and RAG pipeline, and returns the response.
    """
    try:
        generator = get_generator()
        result = generator.generate_response(request.message)
        
        return ChatResponse(
            answer=result["answer"],
            source=result["source"],
            last_updated=result["last_updated"],
            refused=result["refused"]
        )
    except Exception as e:
        # Log the internal error but never expose details to the client
        # (avoids leaking file paths, PII from queries, or stack traces).
        logger.error("Chat endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Service temporarily unavailable. Please try again later."
        )


@router.get("/api/health", response_model=HealthResponse)
async def health_endpoint():
    """
    Returns system status including vector store document count.
    """
    try:
        store = get_store()
        count = store.get_count()
        last_ingestion = store.get_last_ingestion()
        
        return HealthResponse(
            status="healthy",
            vector_store_count=count,
            last_ingestion=last_ingestion,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return HealthResponse(
            status="unhealthy",
            vector_store_count=0,
            last_ingestion=None
        )
