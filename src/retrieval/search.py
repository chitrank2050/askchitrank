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
    source_filter: str | None = None,
) -> list[dict]:
    """Find the most relevant knowledge chunks for a query embedding.

    Performs cosine similarity search over all knowledge_chunks using
    pgvector's <=> operator. Returns chunks ordered by relevance
    (highest similarity first).

    Args:
        query_embedding: Vector embedding of the user question.
            Must match the dimensions of stored embeddings (512).
        db: Active async database session.
        top_k: Maximum number of chunks to return.
            Defaults to settings.TOP_K_RESULTS.
        source_filter: Optional source to restrict search to.
            One of 'resume', 'sanity', 'linkedin'. None searches all.

    Returns:
        List of chunk dicts ordered by similarity descending. Each dict
        contains: id, source, source_id, content, similarity, chunk_index.
        Empty list if no chunks found.

    Example:
        >>> embedding = await embed_query("What projects has Chitrank built?")
        >>> chunks = await search_knowledge_base(embedding, db)
        >>> chunks[0]["similarity"]
        0.92
    """
    top_k = top_k or settings.TOP_K_RESULTS

    # Build embedding as PostgreSQL vector literal
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Base query — cosine distance converted to similarity score
    # 1 - (embedding <=> query) gives similarity: 1.0 = identical
    query = """
        SELECT
            id::text,
            source,
            source_id,
            content,
            chunk_index,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM knowledge_chunks
        {source_clause}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """

    # Optional source filter — restricts search to a single source
    source_clause = ""
    params: dict = {"embedding": embedding_str, "top_k": top_k}

    if source_filter:
        source_clause = "WHERE source = :source"
        params["source"] = source_filter

    query = query.format(source_clause=source_clause)

    result = await db.execute(text(query), params)
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
