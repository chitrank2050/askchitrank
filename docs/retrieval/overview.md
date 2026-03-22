# Retrieval Layer

The retrieval layer finds relevant knowledge chunks for a question, keeps repeated questions out of the LLM when possible, and now decides whether the evidence is strong enough to answer from.

---

## Overview

```text
User question
      ↓
find_exact_cached_response() — exact match?
      ↓ hit                          ↓ miss
Return cached response         embed_query()
Increment hit_count                   ↓
                               find_cached_response() — similarity > 0.95?
                                      ↓ hit                          ↓ miss
                               Return cached response         search_knowledge_base()
                               Increment hit_count                   ↓
                         Wider vector candidate set
                                      ↓
                         Query-aware local reranking
                                      ↓
                         Retrieval confidence assessment
                                      ↓ pass         ↓ fail
                         Feed selected chunks        Return safe fallback
                         to chat layer
                                      ↓
                         store_cached_response()
```

---

## Vector Search

`search_knowledge_base()` still uses pgvector cosine similarity, but the retrieval flow is now three-stage:

1. pull a wider candidate set from the database
2. rerank those candidates locally using cheap heuristics
3. assess whether the final evidence set is confident enough to answer from

The SQL layer still looks conceptually like this:

```sql
SELECT id, source, content,
       1 - (embedding <=> query_vector) AS similarity
FROM knowledge_chunks
ORDER BY embedding <=> query_vector
LIMIT candidate_limit
```

The difference is that top vector hits are no longer used blindly.

---

## Local Reranking

After vector search, the app reranks candidates using:

- lexical overlap with the user question
- query intent like `projects`, `skills`, `experience`, or `feedback`
- source-aware caps so testimonial-heavy content does not dominate every query

Examples:

- project questions bias more strongly toward Sanity project evidence
- skill questions boost resume, Sanity, and LinkedIn skill-heavy content
- feedback questions boost testimonials and recommendations

This is intentionally local and cheap. It improves relevance without adding another provider call.

---

## Retrieval Confidence

The retrieval layer now exposes an explicit confidence assessment so the chat layer can avoid answering from weak evidence.

The confidence gate checks:

- `top_score` (base similarity + custom keyword/source boosts)
- `best_query_coverage`
- whether the boosted score is strong enough to allow low literal overlap

Current configuration comes from:

- `RETRIEVAL_MIN_SIMILARITY`
- `RETRIEVAL_STRONG_SIMILARITY`
- `RETRIEVAL_MIN_QUERY_COVERAGE`

If confidence is too low, the chat layer returns a safe fallback instead of prompting the LLM with weak context.

This is especially useful for questions that are related to Chitrank but not actually supported by the portfolio corpus, such as favorite color or compensation.

---

## Why This Was High ROI

This project has strict free-tier constraints. Adding a reranker model or extra LLM pass would improve relevance, but it would also increase latency, cost, and operational complexity.

The current retrieval design gives most of the practical benefit for this corpus because:

- the corpus is small
- source types are known
- question intent is easy to infer
- broad narrative chunks were the main precision problem
- unsupported questions are common enough that confidence gating pays for itself

---

## Caching (Exact & Semantic)

The response cache stores question → response pairs in two stages to maximize speed and protect API rate limits:

1. **Exact Match Cache**: Before embedding, the system checks for a case-insensitive exact string match. If found, it returns the cached response immediately using absolutely zero API calls.
2. **Semantic Cache**: If no exact match exists, the question is embedded. It is then compared against previously cached question embeddings.

If a cached question is similar enough (cosine similarity > 0.95):

- the cached response is returned
- `hit_count` is incremented
- no LLM call is made

### Why the semantic threshold is `0.95`

The threshold is intentionally strict. A slightly different portfolio question can deserve a meaningfully different answer, so the cache prefers false negatives over stale or over-broad hits.

---

## Scoring Mechanics (top_score)

The retrieval layer does not use raw cosine similarity alone. The final `top_score` used for confidence gating and reranking is calculated as:

`score = semantic_similarity + (lexical_overlap * 0.18) + source_boost`

### Lexical Overlap

The system tokenizes the user question and each context chunk (removing stop words). It then calculates the percentage of question tokens present in the chunk. This gives a massive boost to chunks that contain the exact technical terms or project names mentioned by the user.

### Source & Intent Boosts

Based on keyword intent detection, specific sources receive a `+0.05` to `+0.08` boost:

| Intent | Preferred Sources | Boost |
|--------|-------------------|-------|
| `projects` | `sanity` | +0.08 |
| `skills` | `resume`, `sanity`, `linkedin` | +0.05 |
| `experience`| `resume`, `linkedin` | +0.06 |
| `feedback` | `testimonial`, `linkedin` | +0.08 |

Conversely, some sources receive a **negative boost** (`-0.03` to `-0.05`) if they are unlikely to be the primary factual source for a specific intent (e.g., testimonials for technical project details).

---

### Cache invalidation

| Trigger | Action |
|--------|--------|
| Any ingestion run | `invalidate_cache()` marks active entries stale |
| Sanity webhook | invalidates cache before re-ingesting Sanity content |
| TTL | entries older than `CACHE_TTL_DAYS` are ignored |

### Cache effectiveness

You can inspect cache reuse with:

```sql
SELECT question, hit_count, created_at
FROM response_cache
WHERE invalidated_at IS NULL
ORDER BY hit_count DESC;
```

---

## Files

| File | Responsibility |
|------|----------------|
| `src/retrieval/search.py` | pgvector candidate search, local reranking, and retrieval confidence assessment |
| `src/retrieval/cache.py` | semantic cache lookup, store, and invalidation |
| `src/ingestion/embedder.py` | shared embedding interface for ingestion and retrieval |

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
