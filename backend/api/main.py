"""
FastAPI application factory.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.config.settings import get_settings
from backend.vectorstore.store import get_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: eagerly load the vector store on startup."""
    get_store()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    
    app = FastAPI(
        title="Mutual Fund FAQ API",
        version="1.0.0",
        description="RAG-based API for querying HDFC Mutual Fund details.",
        lifespan=lifespan,
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(router)
        
    return app

app = create_app()
