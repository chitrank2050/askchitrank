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

import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "his",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "with",
}
_PROJECT_TERMS = {
    "project",
    "projects",
    "build",
    "built",
    "portfolio",
    "product",
    "app",
}
_SKILL_TERMS = {"skill", "skills", "stack", "tech", "technology", "technologies"}
_EXPERIENCE_TERMS = {"experience", "years", "career", "worked", "role", "roles"}
_FEEDBACK_TERMS = {
    "testimonial",
    "testimonials",
    "feedback",
    "recommendation",
    "recommendations",
    "colleague",
    "colleagues",
    "manager",
    "say",
}


@dataclass(frozen=True)
class RetrievalConfidenceAssessment:
    """Confidence signals for the selected retrieval set."""

    is_confident: bool
    reason: str
    top_similarity: float
    top_score: float
    best_query_coverage: float
    matched_query_terms: int
    total_query_terms: int


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+#.-]*", text.lower())
        if token not in _STOP_WORDS and len(token) > 1
    }


def _preferred_source_caps(tokens: set[str], default_cap: int) -> dict[str, int]:
    caps = {
        "resume": 2,
        "sanity": 2,
        "linkedin": 2,
        "testimonial": 2,
    }

    if tokens & _PROJECT_TERMS:
        caps["sanity"] = max(default_cap + 2, 4)
        caps["resume"] = 2
        caps["linkedin"] = 1
        caps["testimonial"] = 1
    elif tokens & _SKILL_TERMS:
        caps["resume"] = max(default_cap + 1, 3)
        caps["sanity"] = max(default_cap + 1, 3)
        caps["linkedin"] = 2
        caps["testimonial"] = 1
    elif tokens & _EXPERIENCE_TERMS:
        caps["resume"] = max(default_cap + 1, 3)
        caps["linkedin"] = max(default_cap + 1, 3)
        caps["sanity"] = 2
        caps["testimonial"] = 1
    elif tokens & _FEEDBACK_TERMS:
        caps["testimonial"] = max(default_cap + 1, 3)
        caps["linkedin"] = max(default_cap + 1, 3)
        caps["resume"] = 1
        caps["sanity"] = 1
    else:
        caps["sanity"] = max(default_cap + 1, 3)

    return caps


def _query_overlap(content: str, query_tokens: set[str]) -> tuple[int, float]:
    if not query_tokens:
        return 0, 0.0

    content_tokens = _tokenize(content)
    overlap = query_tokens & content_tokens
    overlap_ratio = len(overlap) / len(query_tokens)
    return len(overlap), overlap_ratio


def _score_chunk(chunk: dict, tokens: set[str]) -> float:
    if not tokens:
        return float(chunk["similarity"])

    _, overlap_ratio = _query_overlap(chunk["content"], tokens)

    score = float(chunk["similarity"])
    score += overlap_ratio * 0.18

    source = chunk["source"]
    source_id = chunk["source_id"].lower()

    if tokens & _PROJECT_TERMS and source == "sanity":
        score += 0.08
    if tokens & _SKILL_TERMS and source in {"resume", "sanity", "linkedin"}:
        score += 0.05
    if tokens & _EXPERIENCE_TERMS and source in {"resume", "linkedin"}:
        score += 0.06
    if tokens & _FEEDBACK_TERMS and source in {"testimonial", "linkedin"}:
        score += 0.08

    if tokens & _PROJECT_TERMS and source == "testimonial":
        score -= 0.05
    if tokens & _SKILL_TERMS and "recommendation" in source_id:
        score -= 0.04
    if tokens & _EXPERIENCE_TERMS and source == "testimonial":
        score -= 0.03

    if "technologies:" in chunk["content"].lower() and tokens & _SKILL_TERMS:
        score += 0.05
    if "project:" in chunk["content"].lower() and tokens & _PROJECT_TERMS:
        score += 0.05
    if "testimonial:" in chunk["content"].lower() and tokens & _FEEDBACK_TERMS:
        score += 0.05

    return score


def _select_diverse_chunks(
    chunks: list[dict],
    query_tokens: set[str],
    top_k: int,
    top_k_per_source: int,
) -> list[dict]:
    source_caps = _preferred_source_caps(query_tokens, top_k_per_source)
    selected: list[dict] = []
    source_counts: dict[str, int] = {}

    for chunk in sorted(
        chunks,
        key=lambda item: (item["score"], item["similarity"]),
        reverse=True,
    ):
        source = chunk["source"]
        cap = source_caps.get(source, top_k_per_source)
        if source_counts.get(source, 0) >= cap:
            continue

        selected.append(chunk)
        source_counts[source] = source_counts.get(source, 0) + 1

        if len(selected) >= top_k:
            break

    return selected


async def search_knowledge_base(
    query_embedding: Sequence[float],
    db: AsyncSession,
    query_text: str | None = None,
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
    candidate_k_per_source = max(top_k_per_source + 3, 5)
    candidate_limit = max(top_k * 4, 16)

    # Pull a wider candidate set first, then apply a cheap local reranker.
    # This keeps retrieval quality higher without extra model calls.
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
        WHERE source_rank <= :candidate_k_per_source
        ORDER BY similarity DESC
        LIMIT :candidate_limit
    """

    result = await db.execute(
        text(query),
        {
            "embedding": embedding_str,
            "candidate_k_per_source": candidate_k_per_source,
            "candidate_limit": candidate_limit,
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

    if not chunks:
        logger.debug("Search returned 0 chunks")
        return []

    if query_text:
        query_tokens = _tokenize(query_text)
        for chunk in chunks:
            matches, coverage = _query_overlap(chunk["content"], query_tokens)
            chunk["query_term_matches"] = matches
            chunk["query_term_coverage"] = round(coverage, 4)
            chunk["score"] = round(_score_chunk(chunk, query_tokens), 4)
        chunks = _select_diverse_chunks(chunks, query_tokens, top_k, top_k_per_source)
    else:
        chunks = chunks[:top_k]

    logger.debug(
        "Search returned {} chunks — top similarity: {} | top score: {}",
        len(chunks),
        chunks[0]["similarity"] if chunks else "n/a",
        chunks[0].get("score", "n/a") if chunks else "n/a",
    )

    return chunks


def assess_retrieval_confidence(
    query_text: str,
    chunks: list[dict],
) -> RetrievalConfidenceAssessment:
    """Determine whether retrieved evidence is strong enough to answer from."""
    if not chunks:
        return RetrievalConfidenceAssessment(
            is_confident=False,
            reason="empty_results",
            top_similarity=0.0,
            top_score=0.0,
            best_query_coverage=0.0,
            matched_query_terms=0,
            total_query_terms=0,
        )

    query_tokens = _tokenize(query_text)
    top_similarity = max(float(chunk["similarity"]) for chunk in chunks)
    top_score = max(float(chunk.get("score", chunk["similarity"])) for chunk in chunks)
    matched_query_terms = max(
        int(chunk.get("query_term_matches", 0)) for chunk in chunks
    )
    best_query_coverage = max(
        float(chunk.get("query_term_coverage", 0.0)) for chunk in chunks
    )

    if not query_tokens:
        is_confident = top_similarity >= settings.RETRIEVAL_MIN_SIMILARITY
        reason = "ok" if is_confident else "low_similarity"
    elif top_similarity >= settings.RETRIEVAL_STRONG_SIMILARITY:
        is_confident = True
        reason = "ok"
    elif top_similarity < settings.RETRIEVAL_MIN_SIMILARITY:
        is_confident = False
        reason = "low_similarity"
    elif best_query_coverage < settings.RETRIEVAL_MIN_QUERY_COVERAGE:
        is_confident = False
        reason = "low_term_coverage"
    else:
        is_confident = True
        reason = "ok"

    logger.debug(
        "Retrieval confidence — confident: {} | reason: {} | top similarity: {} | "
        "top score: {} | best coverage: {}",
        is_confident,
        reason,
        round(top_similarity, 4),
        round(top_score, 4),
        round(best_query_coverage, 4),
    )

    return RetrievalConfidenceAssessment(
        is_confident=is_confident,
        reason=reason,
        top_similarity=round(top_similarity, 4),
        top_score=round(top_score, 4),
        best_query_coverage=round(best_query_coverage, 4),
        matched_query_terms=matched_query_terms,
        total_query_terms=len(query_tokens),
    )
