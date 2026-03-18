# Key Concepts

This page explains the core technologies used in Ask Chitrank in plain language with simple examples. No assumed knowledge.

---

## Embeddings

An embedding converts text into a list of numbers that captures its meaning.

**Simple example:**

```
"I love dogs"   → [0.2, 0.8, 0.1, 0.5, ...]
"I adore dogs"  → [0.2, 0.8, 0.1, 0.5, ...]  ← almost identical numbers
"The sky is blue" → [0.9, 0.1, 0.7, 0.2, ...] ← completely different numbers
```

The numbers for "I love dogs" and "I adore dogs" are very close together because they mean the same thing. The numbers for "The sky is blue" are far away because it's a different topic entirely.

This is how the chatbot finds relevant answers — it converts your question into numbers, then finds knowledge chunks whose numbers are closest to yours.

**In this project:** Voyage AI `voyage-3-lite` converts text into 512 numbers.

---

## Vector Database

A regular database searches by exact values:

```sql
WHERE name = "Chitrank"   -- must match exactly
```

A vector database searches by meaning:

```sql
ORDER BY embedding <=> question_embedding  -- find closest meaning
```

It's a database that can answer "find me text that means something similar to this" instead of "find me text that matches exactly."

**In this project:** Supabase PostgreSQL with the pgvector extension stores and searches 512-dimensional vectors.

---

## RAG (Retrieval-Augmented Generation)

RAG is a technique that gives an LLM specific knowledge before asking it to answer a question.

Without RAG:
```
User: What has Chitrank built?
LLM: [makes things up or says it doesn't know]
```

With RAG:
```
Step 1 — Retrieve relevant info from the knowledge base:
    "Project: Humanform AI — Chitrank built the frontend ecosystem from scratch..."
    "Project: Plural — Chitrank led a team of 3 frontend engineers..."

Step 2 — Give that info to the LLM as context:
    "Here is information about Chitrank. Use only this to answer: [context]"

Step 3 — LLM answers from the context:
    "Chitrank has built Humanform AI, Plural, Hudini..."
```

The LLM doesn't need to know about Chitrank in advance — you feed it the relevant facts at question time.

**In this project:** The knowledge base is resume + Sanity CMS + LinkedIn data, all stored as embeddings in Supabase.

---

## Semantic Cache

A normal cache stores exact matches:

```
Cache key: "What projects has Chitrank built?"
Cache value: "Chitrank has built Humanform, Plural..."

Lookup: "What projects has Chitrank built?" → hit ✅
Lookup: "What has Chitrank worked on?"      → miss ❌ (different string)
```

A semantic cache stores meaning matches:

```
Cache key embedding: [0.2, 0.8, 0.1, ...]  (embedding of the question)
Cache value: "Chitrank has built Humanform, Plural..."

Lookup: "What projects has Chitrank built?" → similarity 1.0 → hit ✅
Lookup: "What has Chitrank worked on?"      → similarity 0.97 → hit ✅
Lookup: "What is the weather today?"        → similarity 0.2  → miss ❌
```

If two questions mean the same thing (similarity above 0.95), the cached answer is returned without calling the LLM — saving time and money.

**In this project:** The `response_cache` table stores question embeddings + responses. Cache is cleared when content is re-ingested.

---

## Prompt Engineering

Prompt engineering is the practice of carefully designing the instructions you give to an LLM to control its behaviour.

**Bad prompt:**
```
Answer questions about Chitrank.
```

The LLM might make things up, go off-topic, or give long rambling answers.

**Good prompt:**
```
You are Ask Chitrank — an AI assistant on Chitrank's portfolio website.

Answer ONLY from the provided context. Never invent facts.
If context is insufficient, say: "I don't have enough information. 
Contact Chitrank at chitrank2050@gmail.com."
Keep answers concise. Refer to Chitrank in third person.
```

The good prompt constrains the LLM's behaviour — it stays on topic, cites real data, and handles unknowns gracefully.

**In this project:** The system prompt in `src/chat/prompt.py` enforces factual accuracy and prevents hallucination.

---

## SSE (Server-Sent Events)

SSE is a way for a server to push data to a browser in real time, one piece at a time.

**Without SSE (normal HTTP):**
```
Client: "What has Chitrank built?"
[waits 3 seconds for full response]
Server: "Chitrank has built Humanform, Plural, Hudini..." [all at once]
```

**With SSE (streaming):**
```
Client: "What has Chitrank built?"
Server: "Chitrank"    [immediately]
Server: " has"        [50ms later]
Server: " built"      [50ms later]
Server: " Humanform," [50ms later]
...
```

Words appear as the LLM generates them — the same experience as ChatGPT. Users see a response immediately instead of waiting for the full answer.

**In this project:** `POST /v1/chat` with `stream: true` returns an SSE stream. Each token is a JSON event:

```
data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "done", "cached": false}
```

---

## Chunking

Large documents can't be stored as single embeddings — the embedding model has a context window limit, and a large chunk is too general to be useful for specific questions.

Chunking splits documents into smaller pieces:

```
Full resume (700 words)
    ↓
Chunk 1: Summary section (80 words)
Chunk 2: Professional Experience section (300 words)
Chunk 3: Technical Skills section (120 words)
...
```

Each chunk is embedded separately. When a question comes in, the most relevant chunk is retrieved — not the entire document.

**In this project:** Resume is split by section headers. Sanity and LinkedIn documents use 500-word chunks with 50-word overlap. The overlap ensures no sentence is cut off at a boundary without context.

---

## Cosine Similarity

Cosine similarity measures how similar two vectors are — a number between -1 and 1 where 1 means identical and 0 means unrelated.

**Simple analogy:** Think of each embedding as an arrow pointing in a direction in space. If two arrows point in nearly the same direction, they're similar. If they point in completely different directions, they're unrelated.

```
"React developer"  → arrow pointing northeast
"Frontend engineer" → arrow pointing northeast (very close)
"Database admin"    → arrow pointing southeast (different direction)
```

Cosine similarity between "React developer" and "Frontend engineer" would be ~0.92.
Cosine similarity between "React developer" and "Database admin" would be ~0.45.

**In this project:** pgvector's `<=>` operator computes cosine distance. We convert to similarity with `1 - distance`. The semantic cache threshold is 0.95 — questions must be very close in meaning to hit the cache.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)