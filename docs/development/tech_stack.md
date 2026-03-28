# Tech Stack

---

## Core Stack

| Layer | Tool | Why |
|------|------|-----|
| LLM | Groq (`meta-llama/llama-4-scout-17b-16e-instruct`) | MoE architecture, better instruction following, fast streaming, and practical free tier |
| Embeddings | Voyage AI `voyage-3-lite` or Local `all-MiniLM-L6-v2` | high-quality 512-dim or zero-cost local 384-dim fallback |
| Vector store | PostgreSQL + pgvector | PostgreSQL extension, no extra vector service |
| Semantic cache | pgvector similarity search | reduces repeated LLM calls |
| Retrieval expansion | local synonym-based mapping | improves recall for short/ambiguous queries without API calls |
| Retrieval reranking | local query-aware heuristics | improves relevance without more provider spend |
| API | FastAPI | async, typed, streaming-friendly |
| Database | Local PostgreSQL for dev, Supabase for prod | simple local iteration plus an easy hosted path |
| Config | pydantic-settings | type-safe configuration |
| Logging | Loguru | structured logging |
| Package manager | uv | fast dependency management |
| Code quality | Ruff | linting and formatting |

---

## Ingestion Stack

| Layer | Tool | Why |
|------|------|-----|
| PDF parsing | pypdf | pure Python, no system deps |
| HTTP client | httpx | async requests for Sanity and downloads |
| Sanity CMS | GROQ HTTP API | direct and simple |
| LinkedIn | CSV export | official export source |

---

## Development-Only Stack

| Layer | Tool | Why |
|------|------|-----|
| Local embeddings | deterministic fake embedder | token-free local retrieval work |
| Seed corpus | fictional seeded resume, projects, LinkedIn, testimonials | realistic local API behavior without real profile data |
| Seed responder | local prompt-aware seeded response builder | avoids Groq calls in `DEV_MODE` |

---

## Why No LangChain or LlamaIndex

The pipeline is still straightforward: parse, structure, embed, retrieve, rerank, generate. Raw application code is easier to audit and tune than a heavier orchestration framework for this project size.

---

## Provider Swap Strategy

Provider-specific logic is intentionally isolated to small files:

- `src/ingestion/embedder.py`
- `src/chat/groq_client.py`

That keeps the blast radius low, but swapping providers is not literally "config only" anymore. The interfaces are stable; the implementations are isolated.

---

## Why The Recent ROI Work Focused Here

The highest-value improvements came from:

- better source representation
- cheaper local reranking
- a zero-cost local dev path

Those changes improved quality and developer speed without undermining the project’s free-tier constraints.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
