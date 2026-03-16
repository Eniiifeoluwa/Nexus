"""
Vector Search Tool — lightweight version (no sentence-transformers / PyTorch).
Uses ChromaDB's built-in default embedding function instead.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "agent_memory"


class VectorSearchTool:
    """Semantic memory store backed by ChromaDB (default embeddings)."""

    def __init__(self) -> None:
        from config.settings import settings
        self._persist_dir = settings.CHROMA_PERSIST_DIR
        self._collection = None
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialised at %s", self._persist_dir)
        except Exception as exc:
            logger.warning("ChromaDB init failed (%s) — memory disabled", exc)
            self._collection = None

    def store(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        if not self._collection:
            return
        try:
            self._collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[str(uuid.uuid4())],
            )
        except Exception as exc:
            logger.warning("Vector store failed: %s", exc)

    def search(self, query: str, top_k: int = 3) -> list[str]:
        if not self._collection:
            return []
        try:
            n = min(top_k, max(self._collection.count(), 1))
            results = self._collection.query(query_texts=[query], n_results=n)
            return results.get("documents", [[]])[0]
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

    def count(self) -> int:
        if not self._collection:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
