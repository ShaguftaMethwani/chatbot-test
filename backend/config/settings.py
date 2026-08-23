"""
Application settings loaded from environment variables via pydantic-settings.

Usage:
    from backend.config.settings import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe application configuration.

    All values can be overridden via environment variables or a .env file
    located in the backend/ directory.
    """

    # ── LLM (Groq) ──────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Embeddings ───────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── ChromaDB ─────────────────────────────────────────────
    chroma_persist_dir: str = "data/chroma_db"
    chroma_collection: str = "mf_facts"

    # ── Retrieval ────────────────────────────────────────────
    top_k: int = 3
    similarity_threshold: float = 0.35

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton across the app)."""
    return Settings()
