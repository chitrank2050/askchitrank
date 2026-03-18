# API Reference

The FastAPI backend exposes three endpoints under `/v1`.
Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Base URL

| Environment | URL |
|---|---|
| Local | `http://localhost:8000` |
| Production | `https://your-deployment.up.railway.app` |

---

## Endpoints

### `GET /v1/health`

Check service health and version.

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

Ask a question about Chitrank. Returns a streamed or full response.

**Request body:**

```json
{
  "question": "What projects has Chitrank built?",
  "session_id": "session-abc123",
  "use_cache": true,
  "stream": true
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `question` | string | required | Question to ask. 1–500 characters. |
| `session_id` | string | required | Browser session ID for conversation history. Generate a UUID on first load and persist in localStorage. |
| `use_cache` | boolean | `true` | Whether to check and populate the semantic cache. Set `false` during testing. |
| `stream` | boolean | `true` | Stream tokens via SSE or return full JSON response. |

**Response — SSE streaming (`stream: true`):**

```
Content-Type: text/event-stream

data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "token", "content": " built"}
data: {"type": "done", "cached": false}
```

Event types:

| Type | Content | When |
|---|---|---|
| `token` | Response text fragment | As tokens stream from LLM |
| `done` | `""` + `cached: bool` | Stream complete |
| `error` | Error message | Pipeline failure |

**Response — full response (`stream: false`):**

```json
{
  "response": "Chitrank has built several projects including Humanform...",
  "cached": false
}
```

**Rate limit:** 30 requests/minute per IP.

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Success |
| `422` | Validation error — check field constraints |
| `429` | Rate limit exceeded |
| `500` | Pipeline error |

---

### `POST /v1/ingest`

Sanity CMS webhook — re-ingests all Sanity content and invalidates
the response cache when portfolio content changes.

**Setup in Sanity:**

1. Go to Sanity dashboard → API → Webhooks → Create webhook
2. URL: `https://your-deployment.up.railway.app/v1/ingest`
3. Trigger: on publish, on delete
4. Secret: set `INGEST_WEBHOOK_SECRET` in Railway environment variables

**Headers:**

| Header | Description |
|---|---|
| `x-sanity-webhook-signature` | HMAC-SHA256 signature. Verified if `INGEST_WEBHOOK_SECRET` is set. |

**Response:**

```json
{
  "status": "ok",
  "chunks_ingested": 12,
  "cache_invalidated": 5
}
```

**Rate limit:** 10 requests/minute per IP.

---

## Rate Limiting

All endpoints use in-memory rate limiting via slowapi. Limits reset
when the server restarts. For multi-instance deployments, swap to
Redis-backed rate limiting.

| Endpoint | Limit |
|---|---|
| `POST /v1/chat` | 30/minute |
| `POST /v1/ingest` | 10/minute |

---

## CORS

The API allows requests from:

- `http://localhost:3000` (Next.js dev)
- `http://localhost:5173` (Vite dev)
- `https://chitrankagnihotri.com` (production portfolio)

Add additional origins to `API_ALLOWED_ORIGINS` in `config.py`.

---

## Frontend Integration

**SSE streaming in JavaScript:**

```javascript
const response = await fetch('https://your-api.railway.app/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: userInput,
    session_id: getOrCreateSessionId(),
    stream: true,
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    const event = JSON.parse(line.replace('data: ', ''));

    if (event.type === 'token') {
      appendToUI(event.content);
    } else if (event.type === 'done') {
      finishStreaming(event.cached);
    } else if (event.type === 'error') {
      showError(event.content);
    }
  }
}
```

**Session ID management:**

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
