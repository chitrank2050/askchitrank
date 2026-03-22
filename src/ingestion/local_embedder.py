"""
Local embedding fallback using sentence-transformers.

Uses all-MiniLM-L6-v2 (384-dim) as a zero-cost alternative
when Voyage AI is unavailable or its free tier changes.

Responsibility: embed text locally. Nothing else.
Does NOT: store embeddings, chunk text, or call external APIs.

Requires: uv sync --extra local-embed

Typical usage:
    from src.ingestion.local_embedder import embed_texts, embed_query

    embeddings = await embed_texts(["chunk 1", "chunk 2"])
    query_embedding = await embed_query("Who is Chitrank?")
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from functools import lru_cache

from src.core.logger import logger

_MODEL_NAME = "all-MiniLM-L6-v2"
_DIMENSIONS = 384


@lru_cache(maxsize=1)
def _get_model():
    """Lazy-load the sentence-transformers model once."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required for local embeddings. "
            "Install with: uv sync --extra local-embed"
        ) from None
    logger.info("Loading local embedding model: {}", _MODEL_NAME)
    return SentenceTransformer(_MODEL_NAME)


def _embed_sync(texts: list[str]) -> list[list[float]]:
    """Synchronous embedding using sentence-transformers."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [emb.tolist() for emb in embeddings]


async def embed_texts(texts: list[str]) -> Sequence[Sequence[float]]:
    """Embed a list of text chunks using the local model.

    Runs the model in a thread pool to avoid blocking the event loop.
    """
    if not texts:
        return []

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _embed_sync, texts)
    logger.info("Embedded {} chunks via local model ({})", len(texts), _MODEL_NAME)
    return result


async def embed_query(query: str) -> Sequence[float]:
    """Embed a single query using the local model."""
    results = await embed_texts([query])
    return results[0]


def get_dimensions() -> int:
    """Return the embedding dimensions for the local model."""
    return _DIMENSIONS
