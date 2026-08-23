"""
Embedder and vector store loader.
Processes chunks and loads them into ChromaDB.
"""
import hashlib
import logging
from typing import List, Dict, Any

from backend.vectorstore.store import get_store

logger = logging.getLogger(__name__)


def generate_id(text: str) -> str:
    """Generate a unique ID based on the hash of the text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def embed_and_store(chunks: List[Dict[str, Any]]):
    """
    Store chunks in the vector store.
    Embeddings are generated automatically by the ChromaDB embedding function.
    """
    if not chunks:
        logger.warning("No chunks provided to embed_and_store.")
        return

    documents = []
    metadatas = []
    ids = []

    for chunk in chunks:
        text = chunk["text"]
        documents.append(text)
        metadatas.append(chunk["metadata"])
        ids.append(generate_id(text))

    store = get_store()
    store.add_documents(documents=documents, metadatas=metadatas, ids=ids)
    logger.info(f"Successfully stored {len(documents)} chunks. Total count: {store.get_count()}")
