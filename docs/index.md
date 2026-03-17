# Ask Chitrank

> RAG-powered AI assistant that answers questions about Chitrank using resume, portfolio, and Sanity CMS data.

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

## Links

| | URL |
|---|---|
| 📚 Documentation | https://chitrank2050.github.io/askchitrank |
| 👤 Portfolio | https://chitrankagnihotri.com |
| 🐳 Docker Image | https://hub.docker.com/r/chitrank2050/askchitrank |

---

## Status

| Phase | Status |
|---|---|
| Database + pgvector setup | ✅ Complete |
| Ingestion pipeline | 📋 In Progress |
| RAG query pipeline | 📋 Planned |
| FastAPI + streaming | 📋 Planned |
| Frontend chat widget | 📋 Planned |