"""
Semantic response cache.

Caches question→response pairs to reduce LLM API costs. When a new
question is semantically similar to a previously answered question
(cosine similarity above threshold), the cached response is returned
immediately without calling the LLM.

Cache invalidation:
    - Automatic: entries expire after CACHE_TTL_DAYS days
    - Manual: call invalidate_cache() to clear all entries
    - Webhook: Sanity webhook calls invalidate_cache() on content update

Responsibility: manage response cache. Nothing else.
Does NOT: embed queries, search knowledge base, or call the LLM.

Typical usage:
    from src.retrieval.cache import find_cached_response, store_cached_response

    # Check cache before calling LLM
    cached = await find_cached_response(query_embedding, db)
    if cached:
        return cached["response"]

    # Store response after LLM call
    await store_cached_response(question, query_embedding, response, chunk_ids, db)
"""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger
from src.db.models import ResponseCache


async def find_cached_response(
    query_embedding: list[float],
    db: AsyncSession,
    threshold: float | None = None,
) -> dict | None:
    """Find a cached response for a semantically similar question.

    Searches the response_cache table for entries with cosine similarity
    above the threshold. Returns the most similar valid (non-invalidated,
    non-expired) entry.

    Also increments the hit_count for the matched entry so we can track
    how effective the cache is over time.

    Args:
        query_embedding: Vector embedding of the current user question.
        db: Active async database session.
        threshold: Minimum cosine similarity to consider a cache hit.
            Defaults to settings.CACHE_SIMILARITY_THRESHOLD (0.95).

    Returns:
        Dict with keys: id, question, response, similarity, hit_count.
        None if no similar cached response found.

    Example:
        >>> cached = await find_cached_response(embedding, db)
        >>> if cached:
        ...     print(f"Cache hit — similarity: {cached['similarity']}")
    """
    threshold = threshold or settings.CACHE_SIMILARITY_THRESHOLD
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # TTL cutoff — ignore entries older than CACHE_TTL_DAYS
    ttl_cutoff = datetime.now(UTC) - timedelta(days=settings.CACHE_TTL_DAYS)

    result = await db.execute(
        text("""
            SELECT
                id::text,
                question,
                response,
                hit_count,
                1 - (question_embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM response_cache
            WHERE invalidated_at IS NULL
              AND created_at > :ttl_cutoff
              AND 1 - (question_embedding <=> CAST(:embedding AS vector)) > :threshold
            ORDER BY question_embedding <=> CAST(:embedding AS vector)
            LIMIT 1
        """),
        {
            "embedding": embedding_str,
            "threshold": threshold,
            "ttl_cutoff": ttl_cutoff,
        },
    )

    row = result.fetchone()
    if not row:
        logger.debug("Cache miss — no similar question found")
        return None

    # Increment hit count — track cache effectiveness
    await db.execute(
        update(ResponseCache)
        .where(ResponseCache.id == row.id)
        .values(hit_count=row.hit_count + 1)
    )
    await db.commit()

    logger.info(
        f"Cache hit — similarity: {round(float(row.similarity), 4)} | "
        f"hit_count: {row.hit_count + 1}"
    )

    return {
        "id": row.id,
        "question": row.question,
        "response": row.response,
        "similarity": round(float(row.similarity), 4),
        "hit_count": row.hit_count + 1,
    }


async def store_cached_response(
    question: str,
    question_embedding: list[float],
    response: str,
    source_chunk_ids: list[str],
    db: AsyncSession,
) -> None:
    """Store a question→response pair in the semantic cache.

    Called after every successful LLM response to populate the cache
    for future similar questions.

    Args:
        question: Original user question text.
        question_embedding: Vector embedding of the question.
        response: Full LLM response text to cache.
        source_chunk_ids: List of knowledge chunk IDs used to generate
            this response — stored for traceability.
        db: Active async database session.

    Example:
        >>> await store_cached_response(
        ...     question="What projects has Chitrank built?",
        ...     question_embedding=embedding,
        ...     response="Chitrank has built...",
        ...     source_chunk_ids=["uuid-1", "uuid-2"],
        ...     db=db,
        ... )
    """
    db.add(
        ResponseCache(
            question=question,
            question_embedding=question_embedding,
            response=response,
            source_chunk_ids=json.dumps(source_chunk_ids),  # store as JSON array
            hit_count=0,
            invalidated_at=None,  # null = valid cache entry
        )
    )
    await db.commit()

    logger.debug(f"Cached response for question: {question[:60]}...")


async def invalidate_cache(db: AsyncSession) -> int:
    """Invalidate all active cache entries.

    Called when knowledge base content changes — e.g. when Sanity CMS
    is updated via webhook or when ingestion is re-run. Marks all
    non-invalidated entries with the current timestamp.

    Args:
        db: Active async database session.

    Returns:
        Number of cache entries invalidated.

    Example:
        >>> count = await invalidate_cache(db)
        >>> print(f"Invalidated {count} cache entries")
    """
    result = await db.execute(
        text("""
            UPDATE response_cache
            SET invalidated_at = :now
            WHERE invalidated_at IS NULL
            RETURNING id
        """),
        {"now": datetime.now(UTC)},
    )
    await db.commit()

    count = len(result.fetchall())
    logger.info(f"Invalidated {count} cache entries")
    return count
