"""
Retrieval package.

Provides two retrieval mechanisms:
    search — pgvector cosine similarity search over knowledge_chunks
    cache  — semantic response cache to reduce LLM API costs

Query flow:
    1. Embed user question (Voyage AI)
    2. Check response_cache — similarity > 0.95 → return cached response
    3. Search knowledge_chunks — return top K most relevant chunks
    4. Feed chunks to LLM as context
    5. Cache the response for future similar questions

Typical usage:
    from src.retrieval.search import search_knowledge_base
    from src.retrieval.cache import find_cached_response, store_cached_response
"""

from .cache import (
    find_cached_response,
    invalidate_cache,
    store_cached_response,
)
from .search import search_knowledge_base

__all__ = [
    "find_cached_response",
    "invalidate_cache",
    "search_knowledge_base",
    "store_cached_response",
]
