# API Reference

The FastAPI backend exposes three endpoints under `/v1`.
Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Authentication

All endpoints except `GET /v1/health` require a Bearer token.

```
Authorization: Bearer YOUR_API_TOKEN
```

Generate your token:

```bash
openssl rand -hex 32
```

Add to `.env.dev` and `.env.prod`:

```bash
API_TOKEN=your-generated-token
```

**What happens without a token:**

```json
{
  "error": {
    "code": 401,
    "type": "MISSING_TOKEN",
    "message": "API token is required. Include it as: Authorization: Bearer <your-token>",
    "request_id": "abc12345"
  }
}
```

**What happens with a wrong token:**

```json
{
  "error": {
    "code": 401,
    "type": "INVALID_TOKEN",
    "message": "Invalid API token. Check your token and try again.",
    "request_id": "abc12345"
  }
}
```

---

## Base URL

| Environment | URL |
|---|---|
| Local | `http://localhost:8000` |
| Production | `https://your-deployment.up.railway.app` |

---

## Endpoints

### `GET /v1/health`

Check service health and version. **Public — no auth required.**

Used by Railway health checks and uptime monitors.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.4.0",
  "timestamp": "2026-03-18T10:00:00+00:00"
}
```

---

### `POST /v1/chat`

Ask a question about Chitrank. Requires Bearer token.

**Request headers:**

```
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
| `question` | string | ✅ | — | Question to ask. 2–500 characters. Cannot be empty or whitespace only. |
| `session_id` | string | ✅ | — | Browser session UUID. Generate once and persist in localStorage. Same ID maintains conversation context. |
| `use_cache` | boolean | ❌ | `true` | Check and populate semantic cache. Set `false` during testing. |
| `stream` | boolean | ❌ | `true` | Stream tokens via SSE (`true`) or return full JSON (`false`). |

**Response — SSE streaming (`stream: true`):**

```
Content-Type: text/event-stream

data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "token", "content": " built"}
data: {"type": "done", "cached": false}
```

| Event type | Fields | When |
|---|---|---|
| `token` | `content: string` | Token arrives from LLM |
| `done` | `cached: boolean` | Stream complete |
| `error` | `content: string` | Pipeline failure |

**Response — full response (`stream: false`):**

```json
{
  "response": "Chitrank has built several projects including Humanform...",
  "cached": false
}
```

**Rate limit:** 30 requests/minute per IP.

**Error responses:**

| Code | Type | When |
|---|---|---|
| 401 | `MISSING_TOKEN` | No Authorization header |
| 401 | `INVALID_TOKEN` | Wrong token |
| 422 | `VALIDATION_ERROR` | Invalid request body |
| 429 | `RATE_LIMITED` | 30/minute exceeded |
| 503 | `EMBEDDING_FAILED` | Voyage AI unavailable |
| 503 | `LLM_FAILED` | Groq unavailable |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

### `POST /v1/ingest`

Sanity CMS webhook — re-ingests content and clears cache.

Protected by `API_TOKEN` passed as a **query parameter** (not Bearer header) because Sanity webhooks cannot send custom authorization headers.

**Webhook URL format:**

```
https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN
```

**Sanity webhook configuration:**

1. Go to [sanity.io/manage](https://sanity.io/manage) → your project → API → Webhooks
2. Click **Add webhook**
3. Fill in:
   - **Name:** Portfolio content sync
   - **URL:** `https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN`
   - **Trigger on:** Create, Update, Delete
   - **Filter:** `_type == "project" || _type == "testimonial"`
4. Save

**Response:**

```json
{
  "status": "ok",
  "chunks_ingested": 12,
}
```

**Rate limit:** 10 requests/minute per IP.

**Error responses:**

| Code | Type | When |
|---|---|---|
| 401 | `MISSING_TOKEN` | No token query param |
| 401 | `INVALID_TOKEN` | Wrong token |
| 429 | `RATE_LIMITED` | 10/minute exceeded |
| 500 | `INGESTION_FAILED` | Re-ingestion error |

---

## Error Response Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": 401,
    "type": "MISSING_TOKEN",
    "message": "Human-readable description of what went wrong",
    "request_id": "abc12345"
  }
}
```

| Field | Description |
|---|---|
| `code` | HTTP status code |
| `type` | Machine-readable error type — use this for programmatic handling |
| `message` | Human-readable description — safe to show to users |
| `request_id` | 8-character request ID for tracing in server logs |

**All error types:**

| Type | Code | Description |
|---|---|---|
| `MISSING_TOKEN` | 401 | Authorization header or token param absent |
| `INVALID_TOKEN` | 401 | Token present but wrong |
| `UNAUTHORIZED` | 403 | Not authorized for this action |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `VALIDATION_ERROR` | 422 | Request body failed schema validation |
| `INVALID_INPUT` | 400 | A specific field has an invalid value |
| `EMBEDDING_FAILED` | 503 | Voyage AI embedding service unavailable |
| `LLM_FAILED` | 503 | Groq LLM service unavailable |
| `INGESTION_FAILED` | 500 | Content ingestion pipeline failed |
| `INVALID_SIGNATURE` | 401 | Webhook signature mismatch |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | External service temporarily unavailable |

---

## Cache Invalidation

The response cache clears automatically on every ingestion:

| Trigger | Action |
|---|---|
| `make ingest` (any source) | Cache cleared before new chunks stored |
| Sanity webhook fires | Cache cleared, then Sanity re-ingested |
| TTL expires | Entries older than `CACHE_TTL_DAYS` (default 7) ignored |

---

## Rate Limiting

In-memory rate limiting via slowapi. Limits reset on server restart.

| Endpoint | Limit |
|---|---|
| `POST /v1/chat` | 30/minute per IP |
| `POST /v1/ingest` | 10/minute per IP |
| `GET /v1/health` | Unlimited |

---

## CORS

The API allows requests from:

- `http://localhost:3000`
- `http://localhost:5173`
- `https://chitrankagnihotri.com`

Add additional origins to `API_ALLOWED_ORIGINS` in `config.py`.

---

## Frontend Integration

**SSE streaming:**

```javascript
async function askChitrank(question, sessionId, apiToken) {
  const response = await fetch('https://your-api.railway.app/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiToken}`,
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

    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const event = JSON.parse(line.replace('data: ', ''));

      if (event.type === 'token') appendToUI(event.content);
      else if (event.type === 'done') finishStreaming(event.cached);
      else if (event.type === 'error') showError(event.content);
    }
  }
}
```

**Session management:**

```javascript
function getOrCreateSessionId() {
  let id = localStorage.getItem('askchitrank-session');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('askchitrank-session', id);
  }
  return id;
}
```

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)