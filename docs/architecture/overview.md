# Architecture Overview

Ask Chitrank is a RAG system built for a small, cost-sensitive portfolio knowledge base. This document explains the main architecture decisions and the recent high-ROI improvements.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                             │
│   Resume PDF      Sanity CMS       LinkedIn CSVs            │
└──────────────┬─────────────┬──────────────────┬────────────┘
               │             │                  │
┌──────────────▼─────────────▼──────────────────▼────────────┐
│                  Ingestion Pipeline                          │
│   Parse → Structure evidence docs → Embed → Store           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              PostgreSQL + pgvector                           │
│   knowledge_chunks    response_cache    conversations        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Retrieval Layer                            │
│   Exact match check → Embed → Semantic cache → Vector search │
│   → Local Rerank → Confidence gate                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Chat Layer                                │
│   Pre-router → Prompt + context → Groq or DEV_MODE output   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                           │
│   POST /v1/chat    GET /v1/chat/safety-metrics              │
│   POST /v1/ingest  GET /v1/health                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Next.js Frontend                            │
│   Chat widget on portfolio — streaming responses            │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### Why RAG over fine-tuning

Fine-tuning a model on personal data is expensive, slow to update, and unnecessary for a portfolio chatbot. RAG retrieves context at request time, so content changes become available immediately after ingestion.

### Why pgvector over a dedicated vector database

For a small knowledge base and low traffic, a dedicated vector database would add operational overhead without much benefit. pgvector keeps the system inside ordinary PostgreSQL, which works well both with local development databases and with hosted options like Supabase in production.

### Why Voyage AI for embeddings

`voyage-3-lite` keeps embedding cost and storage low:

- 512 dimensions
- good English retrieval quality
- generous free tier for this project size

### Why Groq for generation

Groq provides fast response streaming and a practical free tier for portfolio traffic. The app currently uses `meta-llama/llama-4-scout-17b-16e-instruct` (Llama 4 Scout), a 17B-parameter mixture-of-experts model with 16 experts that offers improved instruction following over the previous Llama 3.3 70B at zero additional cost.

### Why two-stage caching

Many portfolio questions are repeated exactly or with very similar wording. The system uses a two-stage cache:

1. **Exact Match**: Case-insensitive string match. Zero API cost (no embedding, no LLM).
2. **Semantic Cache**: Cosine similarity match (> 0.95). Zero LLM cost.

This maximizes speed and protects provider rate limits for popular queries.

### Why improve feature extraction before changing providers

The highest-ROI quality improvement was not switching embedding vendors. It was improving what the system stores and retrieves.

The older approach relied more heavily on broad plain-text source documents. The newer approach creates smaller evidence documents, such as:

- project overview
- project contributions
- project links
- testimonial quotes
- LinkedIn profile summary
- LinkedIn links
- LinkedIn recommendations

This improves retrieval precision without adding more API calls.

### Why local reranking was worth adding

Pure vector similarity is strong, but broad narrative chunks can rank well for many unrelated questions. A cheap local rerank improves precision by looking at:

- lexical overlap with the question
- query intent like `projects`, `skills`, `experience`, or `feedback`
- source-aware caps so testimonials do not dominate factual questions

This is intentionally lightweight because the project has cost constraints.

### Why safety routing was worth adding

Public portfolio bots get many unsupported questions that do not need a full RAG pass:

- "Who are you?"
- "Are you Chitrank?"
- salary or private-detail questions
- explicit prompts
- prompt-injection attempts
- clearly unrelated questions

Adding a cheap pre-router and a retrieval confidence gate was worth it because it:

- saves provider calls on low-value queries
- keeps unsupported questions consistent
- reduces the chance of weak-context hallucinations
- helps the bot keep answering even when backing services are degraded

### Why `DEV_MODE` exists

Local iteration should not require Groq, Voyage, Sanity, and Supabase for every small change.

`DEV_MODE` provides:

- deterministic local embeddings
- fictional seeded source content
- seeded local chat responses
- chat startup without a configured database

This keeps day-to-day development cheap and fast.

### Why no LangChain or LlamaIndex

The system is still a fixed pipeline: parse, structure, embed, retrieve, generate. Raw application code remains easier to reason about than an abstraction layer here.

---

## Data Flow — Ingestion

```
1. Resume PDF is read from data/resume.pdf
2. Resume is split by section headers
3. Sanity project and testimonial records are transformed into retrieval-friendly evidence docs
4. LinkedIn profile and recommendation records are transformed into compact evidence docs
5. If any evidence doc is still too large, chunker.py applies block-aware semantic grouping and chunk packing
6. Evidence documents are embedded with Voyage AI
7. Chunk previews are logged before embeddings are created
8. Chunks are stored in knowledge_chunks
9. Ingestion is idempotent and invalidates stale cache entries
```

In `DEV_MODE`, fictional seed content can stand in for the real resume, Sanity, and LinkedIn sources.

## Data Flow — Query

```
1. User sends question via POST /v1/chat
2. A cheap pre-router checks for identity, private, explicit, prompt-injection, and clearly off-topic questions
3. If not pre-routed, the system checks for an Case-Insensitive **Exact Match Cache** hit
4. If no exact match, the question is embedded
5. **Semantic Cache** is checked for a near-duplicate question (similarity > 0.95)
6. `knowledge_chunks` is searched for a wider vector candidate set if cache misses
7. Candidates are reranked locally using query-aware heuristics
8. Retrieval confidence is assessed before the LLM is called
9. Prompt is built from the selected chunks
10. Groq generates and streams the answer
11. Cache and conversation history are updated
```

In `DEV_MODE`, embeddings and generation are handled locally and the API can respond from fictional seeded data without provider calls.

---

## Database Schema

```
knowledge_chunks
    id UUID PK
    source          VARCHAR  — "resume" | "sanity" | "linkedin" | "testimonial"
    source_id       VARCHAR  — source identifier, sometimes with fragment suffixes like #overview
    content         TEXT     — retrieval-ready evidence text shown to the LLM
    embedding       VECTOR(512)
    chunk_index     INTEGER
    created_at      TIMESTAMPTZ
    updated_at      TIMESTAMPTZ

response_cache
    id UUID PK
    question            TEXT
    question_embedding  VECTOR(512)
    response            TEXT
    source_chunk_ids    TEXT    — JSON array of chunk UUIDs used
    hit_count           INTEGER
    created_at          TIMESTAMPTZ
    invalidated_at      TIMESTAMPTZ  — null = valid

conversations
    id UUID PK
    session_id      VARCHAR  — browser session ID
    role            VARCHAR  — "user" | "assistant"
    content         TEXT
    created_at      TIMESTAMPTZ
```

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
