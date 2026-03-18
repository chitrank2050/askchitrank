"""
Knowledge base similarity search.

Performs pgvector cosine similarity search against the knowledge_chunks
table to find the most relevant chunks for a given user question.

The search uses the <=> operator (cosine distance) which returns values
between 0 and 2 — lower is more similar. We convert to similarity score
(1 - distance) for readability: 1.0 = identical, 0.0 = completely different.

Responsibility: search the knowledge base. Nothing else.
Does NOT: embed queries, manage cache, or call the LLM.

Typical usage:
    from src.retrieval.search import search_knowledge_base

    chunks = await search_knowledge_base(query_embedding, db)
"""

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger


async def search_knowledge_base(
    query_embedding: Sequence[float],
    db: AsyncSession,
    top_k: int | None = None,
    top_k_per_source: int = 2,
) -> list[dict]:
    """Find the most relevant knowledge chunks with source diversity.

    Returns top_k_per_source results per source to prevent any single
    source from dominating results. Testimonials and recommendations
    are rich narrative text that can match any query — source diversity
    ensures factual chunks (skills, projects) always appear.

    Args:
        query_embedding: Vector embedding of the user question.
        db: Active async database session.
        top_k: Maximum total chunks to return. Defaults to settings.TOP_K_RESULTS.
        top_k_per_source: Maximum chunks per source. Default 2.

    Returns:
        List of chunk dicts ordered by similarity descending.
    """
    top_k = top_k or settings.TOP_K_RESULTS
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Use window function to rank within each source then filter
    # This guarantees representation from resume, sanity, and linkedin
    query = """
        WITH ranked AS (
            SELECT
                id::text,
                source,
                source_id,
                content,
                chunk_index,
                1 - (embedding <=> CAST(:embedding AS vector)) AS similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY source
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                ) AS source_rank
            FROM knowledge_chunks
        )
        SELECT id, source, source_id, content, chunk_index, similarity
        FROM ranked
        WHERE source_rank <= :top_k_per_source
        ORDER BY similarity DESC
        LIMIT :top_k
    """

    result = await db.execute(
        text(query),
        {
            "embedding": embedding_str,
            "top_k_per_source": top_k_per_source,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()

    chunks = [
        {
            "id": row.id,
            "source": row.source,
            "source_id": row.source_id,
            "content": row.content,
            "chunk_index": row.chunk_index,
            "similarity": round(float(row.similarity), 4),
        }
        for row in rows
    ]

    logger.debug(
        f"Search returned {len(chunks)} chunks — "
        f"top similarity: {chunks[0]['similarity'] if chunks else 'n/a'}"
    )

    return chunks
