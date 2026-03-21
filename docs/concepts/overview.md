# Key Concepts

This page explains the core ideas behind Ask Chitrank in plain language.

---

## Embeddings

An embedding converts text into a list of numbers that captures meaning.

**Simple example:**

```
"I love dogs"     → [0.2, 0.8, 0.1, 0.5, ...]
"I adore dogs"    → [0.2, 0.8, 0.1, 0.5, ...]
"The sky is blue" → [0.9, 0.1, 0.7, 0.2, ...]
```

The first two are close because they mean nearly the same thing. The third is far away because it is a different topic.

**In this project:** production uses Voyage AI `voyage-3-lite` with 512 dimensions. In `DEV_MODE`, a deterministic local embedder is used so local testing does not spend tokens.

---

## Vector Database

A normal database searches by exact values:

```sql
WHERE name = "Chitrank"
```

A vector database searches by meaning:

```sql
ORDER BY embedding <=> question_embedding
```

**In this project:** Supabase PostgreSQL with the pgvector extension stores and searches embedding vectors.

---

## RAG (Retrieval-Augmented Generation)

RAG means retrieving relevant facts first, then giving them to the LLM before asking for an answer.

Without RAG:

```
User: What has Chitrank built?
LLM: [guesses, hallucinates, or says it does not know]
```

With RAG:

```
Step 1 — Retrieve relevant facts
Step 2 — Add them to the prompt as context
Step 3 — Ask the LLM to answer only from that context
```

**In this project:** the knowledge base comes from the resume, Sanity CMS, testimonials, and LinkedIn exports.

---

## Retrieval-Friendly Documents

Good retrieval depends on more than the embedding model. It also depends on what gets embedded.

Instead of storing every source as one broad text blob, the ingestion layer now creates bounded evidence documents such as:

- project overview
- project contributions
- project links
- testimonial quotes
- LinkedIn profile summary
- LinkedIn links
- LinkedIn recommendations

These smaller, more intentional documents are easier to retrieve accurately for specific questions.

---

## Semantic Cache

A normal cache stores exact string matches.

```
Question: "What projects has Chitrank built?"
```

A semantic cache stores meaning matches.

```
"What projects has Chitrank built?" → hit
"What has Chitrank worked on?"      → hit
"What is the weather today?"        → miss
```

If similarity is above `0.95`, the cached answer is returned and the LLM call is skipped.

**In this project:** the `response_cache` table stores question embeddings and responses, and is invalidated on ingestion.

---

## Prompt Engineering

Prompt engineering is how the system tells the LLM what kind of answer is allowed.

A weak prompt can cause rambling or invented facts.

A strong prompt can say:

- answer only from the provided context
- stay concise
- refer to Chitrank in third person
- redirect off-topic questions
- use the configured contact email when context is insufficient
- clarify that the assistant is not Chitrank
- refuse private, explicit, or prompt-reveal requests when they are not supported

That is what keeps the chatbot grounded.

---

## Safety Pre-Routing

Some questions are not worth sending through the full RAG pipeline.

The chat layer now runs a cheap classification pass before embeddings to catch:

- identity questions like "Who are you?" or "Are you Chitrank?"
- private questions like salary or sensitive personal details
- explicit or sexual questions
- prompt-injection attempts such as "ignore instructions" or "show the system prompt"
- clearly off-topic questions such as weather or sports

For these cases, the app returns a canned response immediately. That improves safety and saves tokens.

---

## SSE (Server-Sent Events)

SSE lets the server push tokens to the browser as they are generated.

Without SSE, the user waits for the full answer.

With SSE:

```
data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "done", "cached": false}
```

This makes the API feel interactive instead of blocking.

---

## Chunking

Large documents are usually too broad to embed as one unit.

Chunking splits them into smaller, more useful pieces.

**In this project:**

- the resume is split by section headers
- Sanity and LinkedIn records are first turned into retrieval-friendly evidence documents
- generic word-count chunking remains as a safety net when a document is still too large

The goal is not just smaller text. The goal is better retrieval precision.

---

## Local Reranking

Vector similarity gets the system close, but not always all the way there.

After the initial vector search, the retrieval layer now applies a cheap local rerank using:

- lexical overlap with the user query
- query intent such as `projects`, `skills`, `experience`, or `feedback`
- source-aware caps so narrative testimonial text does not drown out factual sources

This improves answer quality without adding more provider calls.

---

## Retrieval Confidence Gate

Even after vector search and local reranking, the system should not guess when evidence is weak.

The retrieval layer now checks signals such as:

- top vector similarity
- lexical coverage of the user question
- whether the match is strong enough semantically to trust without exact word overlap

If confidence is too low, the chat layer returns a safe fallback instead of sending weak context to the LLM.

---

## Cosine Similarity

Cosine similarity measures how closely two vectors point in the same direction.

```text
"React developer"   → very close to "Frontend engineer"
"React developer"   → much farther from "Database admin"
```

In this project, pgvector uses cosine distance via `<=>`, and the app converts that to similarity with `1 - distance`.

---

## Why These Changes Matter

The recent improvements were chosen for return on effort, not novelty.

The highest-value changes were:

- improving how source data is represented
- improving how retrieval chooses chunks
- adding cheap safety routing and confidence gating before expensive generation
- adding a fictional seeded dev mode to avoid token spend during local work

For the full reasoning, see [ROI Improvements](roi_improvements.md).

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
