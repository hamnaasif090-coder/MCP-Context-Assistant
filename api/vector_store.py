"""
api/vector_store.py
ChromaDB-backed vector store – fully free, runs in-process.
"""
from __future__ import annotations
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import get_settings
from logger import logger
from api.embeddings import get_embedding_service

settings = get_settings()


class VectorStore:
    """
    Thin wrapper around ChromaDB collection.
    Handles upsert, query, delete, and metadata filtering.
    """

    def __init__(self):
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = get_embedding_service()
        logger.info(f"VectorStore ready – collection '{settings.chroma_collection}'")

    # ── Write ──────────────────────────────────────────────────────────────
    def upsert(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        embeddings = self._embedder.embed(texts)
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.debug(f"Upserted {len(texts)} chunks")
        return ids

    # ── Read ───────────────────────────────────────────────────────────────
    def query(
        self,
        query_text: str,
        top_k: int = None,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or settings.top_k_results
        query_vec = self._embedder.embed_one(query_text)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": min(top_k, self._collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1.0 - dist  # cosine distance → similarity
            if score >= settings.similarity_threshold:
                hits.append({"text": doc, "metadata": meta, "score": round(score, 4)})
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits

    def delete_by_source(self, source: str) -> int:
        results = self._collection.get(where={"source": source})
        ids = results.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> List[str]:
        results = self._collection.get(include=["metadatas"])
        sources = {m.get("source", "") for m in results.get("metadatas", [])}
        return sorted(sources)


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
