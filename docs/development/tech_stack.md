# Tech Stack

---

## Core Stack

| Layer            | Tool                       | Why                                            |
|------------------|----------------------------|------------------------------------------------|
| LLM              | Groq (Llama 3.1 70B)       | Free tier, 10-20x faster than GPU inference    |
| Embeddings       | Voyage AI voyage-3-lite    | 200M tokens/month free, Anthropic recommended  |
| Vector store     | Supabase pgvector          | PostgreSQL extension — no extra service needed |
| Semantic cache   | pgvector similarity search | Reduces LLM calls for repeated questions       |
| API              | FastAPI                    | Async, Pydantic validation, streaming support  |
| Database         | Supabase PostgreSQL        | Free tier, excellent dashboard                 |
| Config           | pydantic-settings          | Type-safe, env var override                    |
| Logging          | Loguru                     | Structured, stdlib interception                |
| Package manager  | uv                         | Fast, PEP 517, lockfile reproducibility        |
| Code quality     | Ruff                       | Linter + formatter, fast                       |
| Changelog        | git-cliff                  | Conventional commit changelog                  |

---

## Ingestion Stack

| Layer            | Tool                       | Why                                            |
|------------------|----------------------------|------------------------------------------------|
| PDF parsing      | pypdf                      | Pure Python, no system dependencies            |
| HTTP client      | httpx                      | Async, used for Sanity API + PDF fetch         |
| Sanity CMS       | GROQ HTTP API              | Direct queries, no SDK needed                  |
| LinkedIn         | CSV export                 | Official LinkedIn data export                  |

---

## Why No LangChain or LlamaIndex

Both frameworks are designed for complex multi-step agent pipelines. A personal portfolio RAG has a fixed, simple pipeline — parse, chunk, embed, retrieve, generate. Raw API calls give full control and the entire pipeline is readable in under 300 lines of code.

---

## Provider Swap Strategy

The system is designed so the LLM and embedding providers can be swapped in one config change:

```bash
# Current — free tier
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-70b-versatile
VOYAGE_API_KEY=...
VOYAGE_MODEL=voyage-3-lite

# Future — when Anthropic API key available
ANTHROPIC_API_KEY=...
# embedding model swap handled in embedder.py
```

No code changes required — only config.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)