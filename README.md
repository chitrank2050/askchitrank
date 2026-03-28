# Ask Chitrank

> RAG-powered AI assistant that answers questions about Chitrank — trained on resume, portfolio, and Sanity CMS data.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Groq](https://img.shields.io/badge/Groq-Llama_4_Scout_17B--16E-orange)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-voyage--3--lite-purple)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/version-0.7.0-brightgreen)

---

## Links

| **Type**            | **URL**                                                             |
|---------------------|---------------------------------------------------------------------|
| 🌐 API              | [Live API](https://askchitrank-production.up.railway.app)           |
| 📚 Documentation    | [Project Documentation](https://chitrank2050.github.io/askchitrank) |
| 👤 Portfolio        | [About me](https://chitrankagnihotri.com)                           |
| ⚡ Vite Chat Widget  | [NPM](https://www.npmjs.com/package/@chitrank2050/ask-widget)       |

---

## What It Does

Ask Chitrank answers questions about Chitrank Agnihotri — his experience, projects, skills, and background. Every answer is grounded in real data from his resume, LinkedIn, and portfolio, preventing hallucination.

**Example questions:**

- "What projects has Chitrank built?"
- "What is his tech stack?"
- "How many years of experience does he have?"
- "What do his colleagues say about him?"

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

## Documentation

- [Setup & Installation](https://chitrank2050.github.io/askchitrank/development/setup/)
- [Architecture Overview](https://chitrank2050.github.io/askchitrank/architecture/overview/)
- [High-ROI Improvements](https://chitrank2050.github.io/askchitrank/concepts/roi_improvements/)
- [Tech Stack](https://chitrank2050.github.io/askchitrank/development/tech_stack/)
- [Database Setup](https://chitrank2050.github.io/askchitrank/development/database/)
- [Ingestion Pipeline](https://chitrank2050.github.io/askchitrank/ingestion/overview/)
- [Retrieval Layer](https://chitrank2050.github.io/askchitrank/retrieval/overview/)

---

## Semantic Caching

Every LLM response is cached in two stages to maximize speed and minimize API limits:
1. **Exact Match Cache**: If the exact same question was asked before, the cached response is instantly returned. This costs absolutely zero API calls (no embedding, no LLM), protecting provider rate limits for frequent queries.
2. **Semantic Cache**: If the exact text isn't cached, the user's question is embedded. If the embedding has a cosine similarity > 0.95 with a previously cached question, the cached response is returned. Zero LLM cost, near-zero latency.

Cache is invalidated automatically when Sanity CMS content changes via webhook.

Retrieval is also expanded using synonym-based query expansion and reranked locally using cheap lexical and source-intent signals. The final `score` incorporates both semantic cosine similarity and query term overlap. For fully local runs, the app can use `sentence-transformers` (`all-MiniLM-L6-v2`) outside `DEV_MODE`, while `DEV_MODE` uses deterministic fake embeddings for token-free iteration.

The chat layer now adds a cheap safety pre-router before embeddings, and a retrieval confidence gate after search. Crucially, the confidence gate evaluates the boosted `top_score` rather than raw semantic similarity alone. This ensures perfectly valid answers correctly pass the threshold by factoring in exact keyword matches and source credibility.

---

## Data Sources

| Source       | Content                                | Retrieval shape |
|--------------|----------------------------------------|-----------------|
| Resume PDF   | Experience, skills, education          | Section-aware chunks with repeated section prefixes |
| Sanity CMS   | Projects and testimonials              | Structured evidence documents plus semantic chunk fallback |
| LinkedIn     | Profile, links, recommendations        | Compact evidence documents plus semantic chunk fallback |

Exact chunk counts vary as source content changes and as grouped evidence documents are emitted during ingestion.

---

## Roadmap

- [x] Phase 1 — Database layer (pgvector, Supabase, Alembic migrations)
- [x] Phase 2 — Ingestion pipeline (resume PDF, Sanity CMS, LinkedIn)
- [x] Phase 3 — Retrieval layer (vector search + semantic cache)
- [x] Phase 4 — Chat layer (prompt engineering + Groq LLM)
- [x] Phase 5 — FastAPI + streaming (chat endpoint)
- [x] Phase 7 — Sanity webhook auto-sync
- [x] Phase 6 — Frontend chat widget (Vite.js)

---

## Known Limitations

- Groq free tier has rate limits (6000 tokens/minute) — sufficient for personal portfolio traffic
- Supabase free tier pauses after 1 week inactivity — first request after pause is slow (~2-3 seconds)
- Response cache threshold (0.95) may miss semantically similar but differently phrased questions — tune based on usage
- Pre-routing and retrieval confidence are heuristic-based, so they should still be tuned against real traffic over time

---

## Safety and Cost Controls

To keep the app safe and stay inside free-tier constraints, the chat flow now includes:

- a cheap pre-router for identity, private, explicit, prompt-injection, and clearly off-topic questions
- a retrieval confidence gate that refuses to guess when evidence is too weak
- stronger prompt rules for identity confusion, private data, explicit content, and prompt-reveal attempts
The chat endpoint now prefers a safe fallback answer over returning a provider error, so the bot keeps responding even when retrieval or generation cannot produce a trustworthy answer.

Pipeline errors and generation failures now log **full tracebacks**, making production debugging much faster without requiring local reproduction.

---

## Deployment (PaaS)

When deploying to platforms like Railway, Render, or Fly.io:

- Use local PostgreSQL for development and keep Supabase connection strings in production-only env files.
- Use **Supabase PGBouncer/Supavisor (port 6543)** instead of direct connections for better pool management.
- Append `?sslmode=require` to your `DATABASE_URL` if connecting from an IPv4-only environment.
- Set `APP_ENV=prod` to disable hot-reloading and enable production logging levels.

---

## Dev Mode

Set `DEV_MODE=true` to avoid real provider calls during local development.

In dev mode:

- embeddings are generated locally with a deterministic fake embedder
- chat responses are produced from fictional seeded data instead of calling Groq
- Sanity, LinkedIn, and resume ingestion can fall back to fictional seeded content
- the API can still run without a configured database, returning fictional seeded chat output

---

## Contributing

This is a personal portfolio project. Issues and PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
