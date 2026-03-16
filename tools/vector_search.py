"""
Vector Search Tool
──────────────────
Provides semantic memory using ChromaDB + Sentence Transformers.

Usage
-----
  store(text, metadata)  → persist to vector DB
  search(query, top_k)   → return top-k semantically similar texts
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "agent_memory"


class VectorSearchTool:
    """Semantic memory store backed by ChromaDB."""

    def __init__(self) -> None:
        from config.settings import settings
        self._persist_dir = settings.CHROMA_PERSIST_DIR
        self._collection = None
        self._embedding_fn = None
        self._init()

    def _init(self) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings as ChromaSettings  # type: ignore
            from chromadb.utils import embedding_functions  # type: ignore

            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            client = chromadb.PersistentClient(
                path=self._persist_dir,
            )
            self._collection = client.get_or_create_collection(
                name=_COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialised at %s", self._persist_dir)
        except Exception as exc:
            logger.warning("ChromaDB init failed (%s) — memory disabled", exc)
            self._collection = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def store(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        if self._collection is None:
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
        if self._collection is None:
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, max(self._collection.count(), 1)),
            )
            docs: list[str] = results.get("documents", [[]])[0]
            return docs
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

    def count(self) -> int:
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
