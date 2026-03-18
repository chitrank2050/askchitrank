"""
Text embedding via Voyage AI.

Converts text chunks into vector representations for
similarity search. Uses voyage-3-lite for cost efficiency
on the free tier (200M tokens/month).

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

# Voyage AI async client — initialised once, reused across calls
_client = voyageai.AsyncClient(api_key=settings.VOYAGE_API_KEY)

# Voyage AI maximum texts per batch request
_BATCH_SIZE = 128


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

    all_embeddings = []

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
    result = await _client.embed(
        texts=[query],
        model=settings.VOYAGE_MODEL,
        input_type="query",  # optimised for retrieval queries
    )
    return result.embeddings[0]
