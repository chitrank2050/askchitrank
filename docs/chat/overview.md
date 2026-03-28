# Chat Layer

The chat layer decides how each question should be answered, builds the prompt when RAG is appropriate, and streams the answer back to the client.

---

## Overview

```text
User question
      ↓
Cheap safety pre-router
      ↓ bypass                     ↓ continue
Canned response              Exact cache → Embed → Semantic cache → Search
                                   ↓
                            Retrieval confidence gate
                                   ↓ pass         ↓ fail
                            build_messages()      Canned fallback
                                   ↓
                            stream_response()
                            Groq API — Llama 4 Scout 17B-16E
                            or DEV_MODE seeded response
                                   ↓
                            Token stream → SSE events
                                   ↓
                            store_cached_response()
                            store_conversation()
```

---

## Files

| File | Responsibility |
|------|----------------|
| `src/chat/safety.py` | cheap pre-routing, canned responses, and in-process safety metrics |
| `src/chat/prompt.py` | system prompt definition and context builder |
| `src/chat/groq_client.py` | Groq generation plus seeded DEV_MODE response path |
| `src/chat/stream.py` | full chat orchestration and SSE output |

---

## System Prompt

The system prompt is responsible for keeping answers:

- factual
- concise
- on-topic
- grounded in retrieved context

Key rules enforced:

- answer only from provided context
- never invent facts
- refer to Chitrank in third person
- clarify that the assistant is not Chitrank
- refuse private, explicit, or prompt-reveal requests when they are unsupported
- redirect off-topic questions
- use the configured contact email when context is insufficient

Retrieved chunks are injected into the system message rather than appended as a separate user message. That keeps conversation history cleaner and reduces confusion about what is instruction versus evidence.

---

## Safety Routing

Before embeddings or retrieval, the chat layer now runs a cheap pre-router for questions that do not need the full RAG pipeline.

It handles:

- identity questions like "Who are you?" or "Are you Chitrank?"
- private questions like salary or sensitive personal details
- explicit questions
- prompt-injection attempts
- clearly off-topic questions

These return deterministic canned responses immediately, which improves safety and saves tokens.

---

## Confidence Gate

After retrieval, the chat layer now checks whether the selected chunks are strong enough to answer from.

The decision uses signals from the retrieval layer such as:

- top_score (boosted semantic relevance)
- lexical coverage of the question
- whether the boosted score is strong enough to trust without literal overlap

If confidence is too low, the chat layer returns a safe fallback instead of sending weak context to the LLM.

---

## Generation

Production generation uses Groq with `meta-llama/llama-4-scout-17b-16e-instruct` (Llama 4 Scout), a 17B-parameter mixture-of-experts model with 16 experts that offers improved instruction following over Llama 3.3 70B at zero additional cost.

| Setting | Value | Reason |
|---------|-------|--------|
| `temperature` | `0.1` | keeps answers factual and controlled |
| `max_tokens` | `1024` | enough for portfolio answers |
| `stream` | `true` by default | supports token streaming |

The provider-specific blast radius is intentionally small. Generation logic is isolated in `src/chat/groq_client.py`.

---

## DEV_MODE

When `DEV_MODE=true`, the chat layer avoids real Groq calls.

Instead it:

- builds the same prompt shape
- reads the injected context
- returns a deterministic seeded response from fictional local data

If the database is also missing, the chat layer can still answer from a compact fictional seeded context block so API work is not blocked.

---

## Always-Answer Behavior

The chat endpoint now prefers a safe answer over a dead-end provider error.

That means:

- unsupported questions return canned responses
- weak retrieval returns a fallback response
- generation failures first try a deterministic answer built directly from the retrieved context, then fall back further if needed
- production chat can degrade safely even if the database is unavailable

This is important for a public portfolio widget, where silence feels broken.

---

## Streaming

Two modes are controlled by the `stream` field in `ChatRequest`.

### SSE streaming (`stream=true`)

```text
data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "done", "cached": false}
```

### Full response (`stream=false`)

```json
{
  "response": "Chitrank has built several projects including...",
  "cached": false
}
```

The chat layer now tries hard to avoid `error` events by returning a safe fallback answer instead.

---

## Conversation History

Each user question and assistant response is stored in `conversations`.

The chat layer fetches the latest 6 messages and includes them in the prompt so follow-up questions keep context inside the same browser session.

That is how questions like this work naturally:

```text
User: What projects has Chitrank built?
Bot: ...

User: Tell me more about the chatbot one
Bot: ...
```

---

## Metrics

Safety and refusal behavior is tracked in-process and exposed at:

`GET /v1/chat/safety-metrics`

The snapshot includes:

- response-route counts such as `pre_router`, `cache_hit`, `llm`, and `error_fallback`
- pre-router categories and reasons
- retrieval confidence fallback reasons
- last-resort fallback reasons

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
