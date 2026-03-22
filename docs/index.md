# Ask Chitrank

> RAG-powered AI assistant that answers questions about Chitrank using resume, portfolio, LinkedIn, and testimonial data.

---

## Links

| **Type**         | **URL**                                                             |
|------------------|---------------------------------------------------------------------|
| 📚 Documentation | [Project Documentation](https://chitrank2050.github.io/askchitrank) |
| 👤 Portfolio     | [About me](https://chitrankagnihotri.com)                           |

---

## What It Does

Ask Chitrank is a conversational AI that answers questions about Chitrank Agnihotri — his experience, projects, skills, and background. It uses RAG to ground every answer in real portfolio data and avoid hallucination.

**Example questions it answers:**

- "What projects has Chitrank built?"
- "What is his tech stack?"
- "How many years of experience does he have?"
- "What do his colleagues say about him?"
- "Has he worked with AI products?"

---

## How It Works

```
User question
    ↓
Cheap safety pre-router
    ↓ bypass                     ↓ continue
Canned response             Exact cache (Case-insensitive match)
                                ↓ hit                        ↓ miss
                        Return cached response      Embed question (Voyage AI / Local Fallback)
                                                        ↓
                                                Check semantic cache (Similarity > 0.95)
                                                        ↓ hit                        ↓ miss
                                                Return cached response      Expand query & Search chunks
                                                                                ↓
                                                                        Query-aware local reranking
                                                                                ↓
                                                                      Retrieval confidence gate
                                                                                ↓ pass         ↓ fail
                                                                        Build prompt + context  Canned fallback
                                                                                ↓
                                                                        Groq LLM (Llama 4 Scout 17B-16E)
                                                                                ↓
                                                                        Store in cache
                                                                                ↓
                                                                        Stream response
```

---

## Knowledge Base Shape

| Source       | Content type                               | Retrieval shape |
|--------------|---------------------------------------------|-----------------|
| Resume PDF   | Experience, skills, education               | Section-aware chunks |
| Sanity CMS   | Projects                                    | Overview, contribution, and link evidence documents |
| Testimonials | Colleague recommendations                   | One evidence document per testimonial |
| LinkedIn     | Profile summary, links, recommendations     | Compact profile and recommendation evidence documents |

Exact chunk counts vary as source content changes and as structured evidence documents are emitted during ingestion.

---

## Recent ROI Improvements

- **LLM Upgrade**: Migrated to **Llama 4 Scout 17B-16E** on Groq for improved reasoning and response quality.
- **Query Expansion**: Synonym-based expansion improves retrieval recall for short or ambiguous queries.
- **Provider Fallback**: Support for local embeddings (`all-MiniLM-L6-v2`) provides a resilient alternative to Voyage AI.
- Structured feature extraction now creates retrieval-friendly evidence documents instead of relying only on broad source blobs.
- Retrieval now combines vector search with cheap local reranking, improving relevance without increasing provider spend.
- Chat now uses a cheap pre-router plus a retrieval confidence gate, improving safety and saving tokens on unsupported questions.
- `DEV_MODE` now supports fictional seeded data and local fake providers so local API work does not burn Groq or Voyage quota.

---

## Roadmap

- [x] Phase 1 — Database layer (pgvector, Supabase, Alembic migrations)
- [x] Phase 2 — Ingestion pipeline (resume PDF, Sanity CMS, LinkedIn)
- [x] Phase 3 — Retrieval layer (vector search + semantic cache)
- [x] Phase 4 — Chat layer (prompt engineering + Groq LLM)
- [x] Phase 5 — FastAPI + streaming (SSE chat endpoint)
- [x] Phase 7 — Sanity webhook auto-sync
- [ ] Phase 6 — Frontend chat widget (Next.js)

---

## Known Limitations

- Groq free tier rate limits still apply in production mode
- Supabase free tier can pause after inactivity, making the first request slower
- The semantic cache threshold of `0.95` is intentionally strict and may miss some near-duplicates
- Local reranking is heuristic-based, so it should still be tuned against real production queries over time
- Safety pre-routing and retrieval confidence are heuristic-based and should also be tuned against real production traffic

---

## Contributing

This is a personal portfolio project. Issues and PRs welcome.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
