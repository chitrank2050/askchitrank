"""
Text embedding via Voyage AI or local sentence-transformers fallback.

Converts text chunks into vector representations for
similarity search. Default provider is Voyage AI (voyage-3-lite)
for cost efficiency on the free tier. Falls back to local
all-MiniLM-L6-v2 when EMBEDDING_PROVIDER=local.

Responsibility: embed text. Nothing else.
Does NOT: store embeddings, chunk text, or load documents.

Typical usage:
    from src.ingestion.embedder import embed_texts, embed_query

    embeddings = await embed_texts(["chunk 1", "chunk 2"])
    query_embedding = await embed_query("Who is Chitrank?")
"""

from collections.abc import Sequence

import voyageai

from src.core.config import settings
from src.core.logger import logger
from src.dev.local_embeddings import (
    embed_text as embed_text_local,
    embed_texts as embed_texts_local,
)

# Voyage AI async client — initialised once, reused across calls
_client = (
    None
    if settings.DEV_MODE or settings.EMBEDDING_PROVIDER == "local"
    else voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)
)

# Voyage AI maximum texts per batch request
_BATCH_SIZE = 128


def _use_local_provider() -> bool:
    """Check if the local sentence-transformers provider is configured."""
    return settings.EMBEDDING_PROVIDER == "local"


async def _embed_texts_local_provider(texts: list[str]) -> Sequence[Sequence[float]]:
    """Embed texts using the local sentence-transformers model."""
    from src.ingestion.local_embedder import embed_texts as st_embed_texts

    return await st_embed_texts(texts)


async def _embed_query_local_provider(query: str) -> Sequence[float]:
    """Embed a query using the local sentence-transformers model."""
    from src.ingestion.local_embedder import embed_query as st_embed_query

    return await st_embed_query(query)


async def embed_texts(texts: list[str]) -> Sequence[Sequence[float]]:
    """Embed a list of text chunks for storage in knowledge_chunks.

    Batches texts in groups of 128 — Voyage AI's maximum batch size.
    Uses 'document' input type optimised for storage and retrieval.

    Args:
        texts: List of text chunks to embed.

    Returns:
        List of embedding vectors, one per input text.
        Each vector has EMBEDDING_DIMENSIONS floats.

    Raises:
        voyageai.APIError: If the Voyage AI API call fails.

    Example:
        >>> embeddings = await embed_texts(["Chitrank built AirSense ML"])
        >>> len(embeddings[0])
        512
    """
    if not texts:
        return []

    if settings.DEV_MODE:
        logger.info(f"Embedded {len(texts)} chunks via local dev embedder")
        return embed_texts_local(texts, settings.EMBEDDING_DIMENSIONS)

    if _use_local_provider():
        return await _embed_texts_local_provider(texts)

    all_embeddings = []

    assert _client is not None

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        result = await _client.embed(
            texts=batch,
            model=settings.VOYAGE_MODEL,
            input_type="document",  # optimised for storage + retrieval
        )
        all_embeddings.extend(result.embeddings)
        logger.debug(f"Embedded batch {i // _BATCH_SIZE + 1} — {len(batch)} texts")

    logger.info(f"Embedded {len(texts)} chunks via {settings.VOYAGE_MODEL}")
    return all_embeddings


async def embed_query(query: str) -> Sequence[float]:
    """Embed a single user query for similarity search.

    Uses 'query' input type optimised for retrieval against
    document embeddings — asymmetric embedding improves retrieval
    accuracy compared to using the same input type for both.

    Args:
        query: User question text to embed.

    Returns:
        Single embedding vector with EMBEDDING_DIMENSIONS floats.

    Raises:
        voyageai.APIError: If the Voyage AI API call fails.

    Example:
        >>> embedding = await embed_query("What projects has Chitrank built?")
        >>> len(embedding)
        512
    """
    if settings.DEV_MODE:
        logger.debug("Embedded query via local dev embedder")
        return embed_text_local(query, settings.EMBEDDING_DIMENSIONS)

    if _use_local_provider():
        return await _embed_query_local_provider(query)

    assert _client is not None

    result = await _client.embed(
        texts=[query],
        model=settings.VOYAGE_MODEL,
        input_type="query",  # optimised for retrieval queries
    )
    return result.embeddings[0]
