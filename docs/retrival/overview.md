# Retrieval Layer

The retrieval layer finds relevant knowledge chunks for a user question
and manages a semantic cache to avoid redundant LLM calls.

---

## Overview

```
User question
      ↓
embed_query() — Voyage AI voyage-3-lite, 'query' input type
      ↓
find_cached_response() — cosine similarity > 0.95?
      ↓ hit                          ↓ miss
Return cached response         search_knowledge_base()
Increment hit_count                   ↓
                               Top K chunks by similarity
                                      ↓
                               Feed to chat layer → LLM
                                      ↓
                               store_cached_response()
```

---

## Similarity Search

`search_knowledge_base()` performs cosine similarity search using pgvector's
`<=>` operator (cosine distance). Results are ordered by relevance with the
highest similarity chunk first.

```sql
SELECT id, source, content,
       1 - (embedding <=> query_vector) AS similarity
FROM knowledge_chunks
ORDER BY embedding <=> query_vector
LIMIT 5
```

The `<=>` operator returns cosine distance (0 = identical, 2 = opposite).
Converted to similarity score: `1 - distance` (1.0 = identical, 0.0 = opposite).

### Optional source filtering

Restrict search to a single source when needed:

```python
chunks = await search_knowledge_base(
    embedding, db, source_filter="resume"
)
```

---

## Semantic Cache

The response cache stores question→response pairs. Before calling the LLM,
the query embedding is compared against all cached question embeddings. If
a similar question was previously answered (similarity > 0.95), the cached
response is returned immediately.

### Why 0.95 threshold

At 0.95 cosine similarity, questions must be nearly identical in meaning to
hit the cache. This is intentionally strict — a slightly different question
might need a meaningfully different answer. Start strict and tune based on usage.

### Cache invalidation

| Trigger              | Action                                                      |
|----------------------|-------------------------------------------------------------|
| Sanity webhook fires | `invalidate_cache()` clears all entries                     |
| Manual               | Call `DELETE /v1/cache` (planned)                           |
| TTL                  | Entries older than `CACHE_TTL_DAYS` (default 7) are ignored |

### Cache effectiveness

`hit_count` is incremented every time a cache entry is served. Query Supabase
to see which questions are being cached and how often:

```sql
SELECT question, hit_count, created_at
FROM response_cache
WHERE invalidated_at IS NULL
ORDER BY hit_count DESC;
```

---

## Files

| File                        | Responsibility                                          |
|-----------------------------|---------------------------------------------------------|
| `src/retrieval/search.py`   | pgvector similarity search against knowledge_chunks     |
| `src/retrieval/cache.py`    | Semantic response cache — lookup, store, invalidate     |
| `src/ingestion/embedder.py` | Voyage AI embedding (shared by ingestion and retrieval) |

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)