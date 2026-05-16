"""
api/embeddings.py
Free local embeddings via sentence-transformers (no API key needed).
Falls back to simple TF-IDF if torch unavailable.
"""
from __future__ import annotations
import hashlib
from typing import List
from functools import lru_cache

from config import get_settings
from logger import logger

settings = get_settings()


class EmbeddingService:
    """
    Wraps sentence-transformers for free local semantic embeddings.
    Model: all-MiniLM-L6-v2  (~80 MB, 384-dim, fast & decent quality)
    """

    def __init__(self):
        self._model = None
        self._model_name = settings.embedding_model
        self._dim = 384  # MiniLM default

    def _load(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded ✓")
        except Exception as e:
            logger.warning(f"sentence-transformers unavailable ({e}). Using fallback.")
            self._model = "fallback"

    def embed(self, texts: List[str]) -> List[List[float]]:
        self._load()
        if self._model == "fallback":
            return self._fallback_embed(texts)
        vecs = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return vecs.tolist()

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]

    # ── Simple TF-IDF fallback (zero dependencies) ─────────────────────────
    def _fallback_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Deterministic 128-dim hash-based vector.
        Not semantic but keeps the app running without torch.
        """
        import math
        results = []
        for text in texts:
            tokens = text.lower().split()
            vec = [0.0] * 128
            for tok in tokens:
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                idx = h % 128
                vec[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            results.append([v / norm for v in vec])
        return results


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
