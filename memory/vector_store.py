"""
Vector Store — Long-Term Memory Layer
──────────────────────────────────────
Provides a persistent semantic memory backed by ChromaDB with
Sentence Transformer embeddings.

Responsibilities
----------------
- Store agent outputs, research summaries, and insights
- Retrieve relevant context for new tasks via cosine similarity
- Namespace collections by task_id to avoid cross-contamination
- Expose a clean interface for both storage and retrieval
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class VectorMemoryStore:
    """
    Long-term semantic memory using ChromaDB.

    Two collections:
      - "global_memory"  → cross-task knowledge (research, insights)
      - "task_{task_id}" → task-scoped working memory
    """

    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        from config.settings import settings
        self._persist_dir = settings.CHROMA_PERSIST_DIR
        self._client = None
        self._embedding_fn = None
        self._ready = False
        self._init()

    # ── Initialisation ─────────────────────────────────────────────────────────

    def _init(self) -> None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self._embedding_fn = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.EMBEDDING_MODEL
                )
            )
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._ready = True
            logger.info(
                "VectorMemoryStore ready (model=%s, path=%s)",
                self.EMBEDDING_MODEL,
                self._persist_dir,
            )
        except Exception as exc:
            logger.warning(
                "VectorMemoryStore unavailable: %s — memory features disabled", exc
            )

    # ── Public API ─────────────────────────────────────────────────────────────

    def store(
        self,
        text: str,
        collection: str = "global_memory",
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Persist a text chunk to the named collection.

        Returns the document ID or None on failure.
        """
        if not self._ready:
            return None
        try:
            col = self._get_or_create(collection)
            doc_id = str(uuid.uuid4())
            col.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        **(metadata or {}),
                    }
                ],
            )
            logger.debug("Stored doc %s in collection '%s'", doc_id, collection)
            return doc_id
        except Exception as exc:
            logger.warning("store() failed: %s", exc)
            return None

    def retrieve(
        self,
        query: str,
        collection: str = "global_memory",
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search against a collection.

        Returns list of { text, metadata, distance }.
        """
        if not self._ready:
            return []
        try:
            col = self._get_or_create(collection)
            n = min(top_k, max(col.count(), 1))
            kwargs: dict[str, Any] = {
                "query_texts": [query],
                "n_results": n,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where

            res = col.query(**kwargs)

            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            return [
                {"text": d, "metadata": m, "distance": dist}
                for d, m, dist in zip(docs, metas, dists)
            ]
        except Exception as exc:
            logger.warning("retrieve() failed: %s", exc)
            return []

    def delete_collection(self, collection: str) -> None:
        """Remove an entire collection (e.g. after task completion)."""
        if not self._ready:
            return
        try:
            self._client.delete_collection(collection)
            logger.info("Deleted collection '%s'", collection)
        except Exception as exc:
            logger.warning("delete_collection() failed: %s", exc)

    def list_collections(self) -> list[str]:
        if not self._ready:
            return []
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception:
            return []

    def collection_count(self, collection: str) -> int:
        if not self._ready:
            return 0
        try:
            return self._get_or_create(collection).count()
        except Exception:
            return 0

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_or_create(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )


# Module-level singleton
_store: VectorMemoryStore | None = None


def get_memory_store() -> VectorMemoryStore:
    global _store
    if _store is None:
        _store = VectorMemoryStore()
    return _store
