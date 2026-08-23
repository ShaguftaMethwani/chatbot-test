"""
ChromaDB client wrapper.
Singleton pattern to ensure only one client connection.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

# Path to the ingestion metadata file (written by the ingestion pipeline)
_INGESTION_META_FILENAME = "ingestion_meta.json"


class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        settings = get_settings()
        logger.info(f"Initializing ChromaDB at {settings.chroma_persist_dir}")
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._persist_dir = settings.chroma_persist_dir
        
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Upsert documents into ChromaDB."""
        logger.info(f"Upserting {len(documents)} documents into ChromaDB")
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(
        self,
        query_texts: list[str],
        n_results: Optional[int] = None,
        where: Optional[dict] = None,
    ):
        """Query the vector store, optionally filtering by metadata.

        Args:
            query_texts: List of query strings to embed and search.
            n_results: Number of results to return (defaults to settings.top_k).
            where: Optional ChromaDB metadata filter dict,
                   e.g. ``{"scheme_name": "HDFC Mid-Cap Opportunities Fund"}``.
        """
        if n_results is None:
            n_results = get_settings().top_k

        kwargs = {
            "query_texts": query_texts,
            "n_results": n_results,
        }
        if where is not None:
            kwargs["where"] = where

        return self.collection.query(**kwargs)

    def get_count(self) -> int:
        """Get total number of documents in collection."""
        return self.collection.count()

    def get_last_ingestion(self) -> Optional[str]:
        """Return the ISO timestamp of the last successful ingestion, or None."""
        meta_path = Path(self._persist_dir) / _INGESTION_META_FILENAME
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                return data.get("last_ingestion")
            except Exception as e:
                logger.warning("Failed to read ingestion metadata: %s", e)
        return None

    def set_last_ingestion(self, timestamp: str):
        """Persist the timestamp of the last successful ingestion."""
        meta_path = Path(self._persist_dir) / _INGESTION_META_FILENAME
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps({"last_ingestion": timestamp}),
            encoding="utf-8",
        )


def get_store() -> VectorStore:
    """Return the singleton VectorStore instance."""
    return VectorStore()
