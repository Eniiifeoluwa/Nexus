"""
Vector Store — Long-Term Memory (lightweight, no PyTorch).
Uses ChromaDB with its built-in default embedding function.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class VectorMemoryStore:
    def __init__(self) -> None:
        from config.settings import settings
        self._persist_dir = settings.CHROMA_PERSIST_DIR
        self._client = None
        self._ready = False
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._ready = True
            logger.info("VectorMemoryStore ready (path=%s)", self._persist_dir)
        except Exception as exc:
            logger.warning("VectorMemoryStore unavailable: %s", exc)

    def store(self, text: str, collection: str = "global_memory",
              metadata: dict[str, Any] | None = None) -> str | None:
        if not self._ready:
            return None
        try:
            col = self._get_or_create(collection)
            doc_id = str(uuid.uuid4())
            col.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"timestamp": datetime.utcnow().isoformat(), **(metadata or {})}],
            )
            return doc_id
        except Exception as exc:
            logger.warning("store() failed: %s", exc)
            return None

    def retrieve(self, query: str, collection: str = "global_memory",
                 top_k: int = 5) -> list[dict[str, Any]]:
        if not self._ready:
            return []
        try:
            col = self._get_or_create(collection)
            n = min(top_k, max(col.count(), 1))
            res = col.query(query_texts=[query], n_results=n,
                            include=["documents", "metadatas", "distances"])
            docs  = res.get("documents",  [[]])[0]
            metas = res.get("metadatas",  [[]])[0]
            dists = res.get("distances",  [[]])[0]
            return [{"text": d, "metadata": m, "distance": dist}
                    for d, m, dist in zip(docs, metas, dists)]
        except Exception as exc:
            logger.warning("retrieve() failed: %s", exc)
            return []

    def list_collections(self) -> list[str]:
        if not self._ready:
            return []
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception:
            return []

    def _get_or_create(self, name: str):
        return self._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )


_store: VectorMemoryStore | None = None

def get_memory_store() -> VectorMemoryStore:
    global _store
    if _store is None:
        _store = VectorMemoryStore()
    return _store
