# Architecture Overview

Ask Chitrank is a RAG (Retrieval-Augmented Generation) system. This document explains the architecture decisions and data flow.

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
│   Parse → Chunk → Embed (Voyage AI) → Store                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Supabase PostgreSQL + pgvector                  │
│   knowledge_chunks    response_cache    conversations        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Retrieval Layer                            │
│   Embed question → Cache lookup → Vector search             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Chat Layer                                │
│   System prompt + context → Groq LLM → Stream response      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                           │
│   POST /v1/chat    POST /v1/ingest    GET /v1/health        │
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

Fine-tuning a model on personal data is expensive, slow to update, and overkill for a personal portfolio chatbot. RAG retrieves relevant context at query time — when the resume or portfolio updates, re-ingest and the chatbot is immediately current. No retraining required.

### Why pgvector over a dedicated vector database

Pinecone, Weaviate, and Qdrant are purpose-built vector databases with excellent performance at scale. For a personal portfolio chatbot with low traffic and a small knowledge base (~22 chunks), a dedicated vector database adds operational overhead without benefit.

pgvector is a PostgreSQL extension — it runs inside the existing Supabase database, meaning one less service to manage, one less bill to pay, and no context-switching between database clients.

### Why Voyage AI for embeddings

Anthropic recommends Voyage AI as their embedding partner. `voyage-3-lite` produces 512-dimensional embeddings — smaller than OpenAI's 1536 dimensions, which means faster similarity search and lower storage costs. Quality is competitive with OpenAI for English text retrieval tasks.

Free tier: 200M tokens/month — more than sufficient for a personal portfolio with low traffic.

### Why Groq for LLM inference

Groq's LPU (Language Processing Unit) hardware delivers inference speeds 10-20x faster than GPU-based providers. Llama 3.1 70B on Groq is free up to rate limits and produces high-quality conversational responses.

When traffic grows or Claude API access is available, the LLM client is swapped in one config change — the rest of the system is provider-agnostic.

### Why semantic caching

Every LLM call costs money and latency. A personal portfolio receives many semantically identical questions — "What has Chitrank built?" and "What projects has he worked on?" mean the same thing.

Semantic caching embeds the question and checks if a similar question was already answered. Above a 0.95 cosine similarity threshold, the cached response is returned immediately — zero LLM cost, near-zero latency.

Cache entries are invalidated via Sanity webhook when portfolio content changes.

### No LangChain or LlamaIndex

Both frameworks are designed for complex multi-step agent pipelines with many data sources. A personal portfolio RAG has a fixed, simple pipeline — parse, chunk, embed, retrieve, generate. Framework abstractions add complexity without benefit here.

Raw API calls give full control over prompt structure, streaming behaviour, and error handling.

---

## Data Flow — Ingestion

```
1. Resume PDF read from data/resume.pdf → text extracted via pypdf
2. Resume split by section headers (Summary, Experience, Skills...)
3. Sanity CMS queried via GROQ API → Projects + Testimonials
4. LinkedIn CSVs read from data/linkedin/ → Recommendations, Positions, Skills
5. Each document chunk embedded via Voyage AI voyage-3-lite → 512-dim vector
6. Chunk + embedding stored in knowledge_chunks table
7. Ingestion idempotent — re-running clears and re-ingests source
```

## Data Flow — Query

```
1. User sends question via POST /v1/chat
2. Question embedded via Voyage AI (query input type)
3. Check response_cache — cosine similarity > 0.95?
   → Cache hit: return cached response, increment hit_count
   → Cache miss: continue
4. Search knowledge_chunks — top 5 by cosine similarity
5. Build prompt: system prompt + retrieved chunks + question
6. Call Groq API with Llama 3.1 70B — stream response
7. Store question + response in response_cache
8. Stream response to client via Server-Sent Events
```

---

## Database Schema

```
knowledge_chunks
    id UUID PK
    source          VARCHAR  — "resume" | "sanity" | "linkedin"
    source_id       VARCHAR  — section name, Sanity doc ID, or CSV row identifier
    content         TEXT     — raw chunk text shown to LLM
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