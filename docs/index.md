# Ask Chitrank

> RAG-powered AI assistant that answers questions about Chitrank using resume, portfolio, and Sanity CMS data.

---

## Links

| **Type**         | **URL**                                                             |
|------------------|---------------------------------------------------------------------|
| 📚 Documentation | [Project Documentation](https://chitrank2050.github.io/askchitrank) |
| 👤 Portfolio     | [About me](https://chitrankagnihotri.com)                           |

---

## What It Does

Ask Chitrank is a conversational AI that answers questions about Chitrank Agnihotri — his experience, projects, skills, and background. It uses Retrieval-Augmented Generation (RAG) to ground every answer in real data from his resume and portfolio, preventing hallucination.

**Example questions it answers:**

- "What projects has Chitrank built?"
- "What is his tech stack?"
- "How many years of experience does he have?"
- "Has he worked with machine learning?"

---

## How It Works

```
User question
    ↓
Embed question (Voyage AI)
    ↓
Check semantic cache (pgvector similarity search)
    ↓ hit                        ↓ miss
Return cached response      Search knowledge base
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