# Ask Chitrank

> RAG-powered AI assistant that answers questions about Chitrank — trained on resume, portfolio, and Sanity CMS data.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Groq](https://img.shields.io/badge/Groq-Llama_3.1_70B-orange)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-voyage--3--lite-purple)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/version-0.3.0-brightgreen)

---

## Links

| **Type**         | **URL**                                                             |
|------------------|---------------------------------------------------------------------|
| 📚 Documentation | [Project Documentation](https://chitrank2050.github.io/askchitrank) |
| 👤 Portfolio     | [About me](https://chitrankagnihotri.com)                           |

---

## What It Does

Ask Chitrank answers questions about Chitrank Agnihotri — his experience, projects, skills, and background. Every answer is grounded in real data from his resume and portfolio, preventing hallucination.

**Example questions:**

- "What projects has Chitrank built?"
- "What is his tech stack?"
- "How many years of experience does he have?"
- "Has he worked with machine learning?"

---

## How It Works

```
User question
    ↓
Embed question (Voyage AI voyage-3-lite)
    ↓
Check semantic cache (pgvector cosine similarity > 0.95)
    ↓ hit                        ↓ miss
Return cached response      Search knowledge_chunks
                                ↓
                            Top 5 relevant chunks
                                ↓
                            Build prompt + context
                                ↓
                            Groq LLM (Llama 3.1 70B)
                                ↓
                            Store in cache
                                ↓
                            Stream response
```

---

## Documentation

- [Setup & Installation](https://chitrank2050.github.io/askchitrank/development/setup/)
- [Architecture Overview](https://chitrank2050.github.io/askchitrank/architecture/overview/)
- [Tech Stack](https://chitrank2050.github.io/askchitrank/development/tech_stack/)
- [Database Setup](https://chitrank2050.github.io/askchitrank/development/database/)

---

## Semantic Caching

Every LLM response is cached by question embedding. When a new question has cosine similarity > 0.95 with a cached question, the cached response is returned immediately — zero LLM cost, near-zero latency.

Cache is invalidated automatically when Sanity CMS content changes via webhook.

---

## Data Sources

| Source | Content | Sync method |
|---|---|---|
| Resume PDF | Experience, skills, education | Manual re-ingest |
| Sanity CMS | Projects, blog posts, portfolio | Webhook auto-sync |

---

## Roadmap

- [x] Phase 1 — Database layer (pgvector, Supabase, Alembic migrations)
- [ ] Phase 2 — Ingestion pipeline (resume PDF + Sanity CMS)
- [ ] Phase 3 — RAG query pipeline (retrieval + Groq LLM)
- [ ] Phase 4 — FastAPI + streaming (chat endpoint)
- [ ] Phase 5 — Frontend chat widget (Next.js)
- [ ] Phase 6 — Sanity webhook auto-sync

---

## Known Limitations

- Groq free tier has rate limits (6000 tokens/minute) — sufficient for personal portfolio traffic
- Supabase free tier pauses after 1 week inactivity — first request after pause is slow (~2-3 seconds)
- Response cache threshold (0.95) may miss semantically similar but differently phrased questions — tune based on usage

---

## Contributing

This is a personal portfolio project. Issues and PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).