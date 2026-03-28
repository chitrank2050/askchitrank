# API Reference

The FastAPI backend exposes four endpoints under `/v1`. Interactive docs are available at `/docs` and `/redoc`.

---

## Authentication

All endpoints except `GET /v1/health` require authentication.

### Bearer token

Used by chat endpoints:

```text
Authorization: Bearer YOUR_API_TOKEN
```

### Query token

Used by the Sanity webhook on `POST /v1/ingest`:

```text
https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN
```

Generate a token with:

```bash
openssl rand -hex 32
```

---

## Base URL

| Environment | URL |
|---|---|
| Local | `http://localhost:8000` |
| Production | `https://your-deployment.up.railway.app` |

---

## Development Mode

When `DEV_MODE=true`:

- chat uses fictional seeded data instead of calling Groq and Voyage
- the API can answer chat requests without a configured database
- `use_cache=false` is no longer the main local cost-saving tool, because dev mode avoids provider calls entirely

This is the recommended way to do token-free local API work.

---

## Endpoints

### `GET /v1/health`

Public endpoint. No auth required.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.6.1",
  "timestamp": "2026-03-19T10:00:00+00:00"
}
```

---

### `POST /v1/chat`

Ask a question about Chitrank.

**Request headers:**

```text
Authorization: Bearer YOUR_API_TOKEN
Content-Type: application/json
```

**Request body:**

```json
{
  "question": "What projects has Chitrank built?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "use_cache": true,
  "stream": true
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `question` | string | ✅ | — | Question to ask. 2–500 characters. |
| `session_id` | string | ✅ | — | Browser session ID. Reuse it for multi-turn chat. |
| `use_cache` | boolean | ❌ | `true` | Check and populate semantic cache. |
| `stream` | boolean | ❌ | `true` | Stream via SSE or return one JSON response. |

**SSE response (`stream: true`):**

```text
Content-Type: text/event-stream

data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "done", "cached": false}
```

| Event type | Fields | When |
|---|---|---|
| `token` | `content: string` | token arrives |
| `done` | `cached: boolean` | stream completes |

**JSON response (`stream: false`):**

```json
{
  "response": "Chitrank has built several projects including...",
  "cached": false
}
```

**Safety behavior:**

- obvious identity, private, explicit, prompt-injection, and clearly off-topic questions are answered by a cheap pre-router before embeddings
- weak retrieval results are answered with a safe fallback instead of calling the LLM
- if retrieval is good but generation fails, the API can answer directly from retrieved context for common structured questions
- provider or database problems prefer a safe fallback answer over a dead-end chat error

**Rate limit:** `30/minute` per IP.

**Common errors:**

| Code | Type | When |
|---|---|---|
| 401 | `MISSING_TOKEN` | no Authorization header |
| 401 | `INVALID_TOKEN` | wrong token |
| 422 | `VALIDATION_ERROR` | invalid request body |
| 429 | `RATE_LIMITED` | limit exceeded |

Provider failures usually degrade to a normal fallback answer instead of an API error.

---

### `GET /v1/chat/safety-metrics`

Returns in-process counters for the chat safety layer.

**Request headers:**

```text
Authorization: Bearer YOUR_API_TOKEN
```

**Response:**

```json
{
  "started_at": "2026-03-20T08:00:00+00:00",
  "uptime_seconds": 3600,
  "totals": {
    "answers_returned_total": 42,
    "requests_total": 42
  },
  "response_routes": {
    "cache_hit": 9,
    "confidence_fallback": 3,
    "llm": 20,
    "pre_router": 8,
    "error_fallback": 2
  },
  "pre_router_categories": {
    "identity": 3,
    "off_topic": 2,
    "private": 2,
    "prompt_injection": 1
  },
  "pre_router_reasons": {
    "assistant_identity": 2,
    "compensation": 1
  },
  "retrieval_gate_reasons": {
    "low_similarity": 2,
    "low_term_coverage": 1
  },
  "fallback_reasons": {
    "generation_failure": 1
  }
}
```

These counters reset on process restart because they are stored in-process.

---

### `POST /v1/ingest`

Sanity CMS webhook endpoint. It invalidates cache and re-ingests Sanity content.

**Webhook URL:**

```text
https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN
```

**Sanity webhook configuration:**

1. Go to `sanity.io/manage`
2. Open your project → API → Webhooks
3. Add webhook
4. Set:
   - Name: `Portfolio content sync`
   - URL: `https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN`
   - Trigger on: `Create`, `Update`, `Delete`
   - Filter: `_type == "project" || _type == "testimonial"`

**Response:**

```json
{
  "status": "ok",
  "chunks_ingested": 12
}
```

When `DEV_MODE=true` and no database is configured, the endpoint can return:

```json
{
  "status": "ok",
  "chunks_ingested": 0,
  "mode": "dev"
}
```

**Rate limit:** `10/minute` per IP.

**Common errors:**

| Code | Type | When |
|---|---|---|
| 401 | `MISSING_TOKEN` | no token query param |
| 401 | `INVALID_TOKEN` | wrong token |
| 429 | `RATE_LIMITED` | limit exceeded |
| 503 | `SERVICE_UNAVAILABLE` | database unavailable in non-dev mode |
| 500 | `INGESTION_FAILED` | ingestion pipeline failed |

---

## Error Format

All errors use the same shape:

```json
{
  "error": {
    "code": 401,
    "type": "MISSING_TOKEN",
    "message": "Human-readable description",
    "request_id": "abc12345"
  }
}
```

| Field | Description |
|---|---|
| `code` | HTTP status code |
| `type` | machine-readable error type |
| `message` | safe human-readable description |
| `request_id` | request trace ID from middleware |

**Current error types:**

| Type | Code | Description |
|---|---|---|
| `MISSING_TOKEN` | 401 | auth header or query token missing |
| `INVALID_TOKEN` | 401 | token provided but incorrect |
| `UNAUTHORIZED` | 403 | not authorized for action |
| `RATE_LIMITED` | 429 | rate limit exceeded |
| `VALIDATION_ERROR` | 422 | request body validation failed |
| `INVALID_INPUT` | 400 | field value invalid |
| `EMBEDDING_FAILED` | 503 | embedding provider unavailable |
| `LLM_FAILED` | 503 | language model provider unavailable |
| `INGESTION_FAILED` | 500 | ingestion failed |
| `SERVICE_UNAVAILABLE` | 503 | required backing service unavailable |
| `INTERNAL_ERROR` | 500 | unexpected server error |

The chat endpoint now tries to avoid surfacing provider errors directly by returning a safe fallback answer instead.

---

## Cache Invalidation

| Trigger | Action |
|---|---|
| `make ingest` | cache invalidated before storing new chunks |
| Sanity webhook | cache invalidated before Sanity re-ingestion |
| TTL expiry | old cache entries are ignored |

---

## Rate Limiting

| Endpoint | Limit |
|---|---|
| `POST /v1/chat` | `30/minute` per IP |
| `GET /v1/chat/safety-metrics` | unlimited |
| `POST /v1/ingest` | `10/minute` per IP |
| `GET /v1/health` | unlimited |

---

## Frontend Integration

```javascript
async function askChitrank(question, sessionId, apiToken) {
  const response = await fetch("https://your-api.railway.app/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiToken}`,
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      stream: true,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const lines = decoder.decode(value).split("\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.replace("data: ", ""));

      if (event.type === "token") appendToUI(event.content);
      else if (event.type === "done") finishStreaming(event.cached);
    }
  }
}
```

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
