# Safety Routing

This page explains the new chat safety layer and why it was added before any extra model calls.

---

## What Problem It Solves

A portfolio bot gets a predictable set of low-value questions:

- "Who are you?"
- "Are you Chitrank?"
- "How much do you earn?"
- explicit or abusive prompts
- prompt-injection attempts
- clearly unrelated questions like weather or sports

Those do not need embeddings, retrieval, or generation to answer well.

The system also gets borderline questions that look related to Chitrank but are not actually grounded in the knowledge base, such as favorite color or other unsupported personal preferences.

Without a safety layer, those cases waste tokens or create pressure for the model to guess.

---

## New Flow

```text
User question
    ↓
Pre-router
    ↓ bypass                         ↓ continue
Canned response                Embeddings + cache + retrieval
                                      ↓
                              Retrieval confidence gate
                                      ↓ pass         ↓ fail
                              LLM generation         Canned fallback
```

The important design rule is simple:

- if the question is obviously unsupported, answer before RAG
- if retrieval is weak, answer without the LLM
- if generation fails, still return a safe fallback

That keeps the bot responsive and reduces unnecessary spend.

---

## Pre-Router Categories

The pre-router currently handles:

- `identity`
  Questions about who the assistant is or whether it is Chitrank.
- `private`
  Salary, compensation, or sensitive personal-detail requests.
- `explicit`
  Sexual or explicit prompts.
- `prompt_injection`
  Requests to reveal prompts or ignore system rules.
- `off_topic`
  Clearly unrelated questions such as weather or sports.

Each category maps to a deterministic canned response.

---

## Retrieval Confidence

The retrieval gate protects the model from weak evidence. It looks at:

- top similarity from pgvector
- best lexical coverage of the user question across selected chunks
- a stronger semantic-similarity override for queries that match well without literal word overlap

If confidence is too low, the app returns a fallback such as:

> I don't have enough verified portfolio information to answer that confidently.

That is better than sending weak context to the LLM and hoping for the best.

---

## Always-Answer Policy

The chat endpoint now prefers safe fallbacks over provider errors.

That means:

- unsupported questions still get a useful response
- retrieval failures still get a useful response
- generation failures still get a useful response
- database loss in chat mode degrades to a safe answer instead of a hard `503`

This is especially important for a public-facing portfolio widget, where silence feels broken.

---

## Metrics

Safety decisions are tracked in-process and exposed through:

`GET /v1/chat/safety-metrics`

The snapshot includes:

- request and answer totals
- final response routes such as `pre_router`, `cache_hit`, `llm`, or `error_fallback`
- pre-router category counts
- retrieval-gate fallback reasons
- last-resort fallback reasons

These counters reset on process restart, which is acceptable for this lightweight deployment model.

---

## Why This Was High ROI

This change was high ROI because it improves two things at once:

- safety and consistency for unsupported questions
- token efficiency on the exact requests that do not need model calls

For a small, cost-sensitive RAG app, that is a better first move than adding another model or more orchestration complexity.

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
