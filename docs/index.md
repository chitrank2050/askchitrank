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

Ask Chitrank is a conversational AI that answers questions about Chitrank Agnihotri — his experience, projects, skills, and background. It uses Retrieval-Augmented Generation (RAG) to ground every answer in real data from his resume, LinkedIn, and portfolio, preventing hallucination.

**Example questions it answers:**

- "What projects has Chitrank built?"
- "What is his tech stack?"
- "How many years of experience does he have?"
- "What do his colleagues say about him?"
- "Has he worked with AI companies?"

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

## Knowledge Base

| Source     | Content                                | Chunks |
|------------|----------------------------------------|--------|
| Resume PDF | Experience, skills, education          | 6      |
| Sanity CMS | Projects, testimonials                 | 12     |
| LinkedIn   | Recommendations, positions, skills     | 4      |
| **Total**  |                                        | **22** |

---

## Roadmap

- [x] Phase 1 — Database layer (pgvector, Supabase, Alembic migrations)
- [x] Phase 2 — Ingestion pipeline (resume PDF, Sanity CMS, LinkedIn)
- [x] Phase 3 — Retrieval layer (vector search + semantic cache)
- [x] Phase 4 — Chat layer (prompt engineering + Groq LLM)
- [x] Phase 5 — FastAPI + streaming (SSE chat endpoint)
- [ ] Phase 6 — Sanity webhook auto-sync + Railway deployment
- [ ] Phase 7 — Frontend chat widget (Next.js)

---

## Known Limitations

- Groq free tier: 6000 tokens/minute — sufficient for personal portfolio traffic
- Supabase free tier pauses after 1 week inactivity — first request after pause is slow (~2-3 seconds)
- Response cache threshold (0.95) may miss semantically similar but differently phrased questions
- voyage-3-lite similarity scores are lower than OpenAI embeddings numerically — ranking is correct even when scores appear low

---

## Contributing

This is a personal portfolio project. Issues and PRs welcome.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)