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
| `session_id` | string | required | Browser session ID for conversation history. Generate a UUID on first load and persist in localStorage. Pass the same ID across requests to maintain multi-turn context. |
| `use_cache` | boolean | `true` | Check and populate the semantic cache. Set `false` during testing. |
| `stream` | boolean | `true` | Stream tokens via SSE or return full JSON response. |

**Response — SSE streaming (`stream: true`):**

```
Content-Type: text/event-stream

data: {"type": "token", "content": "Chitrank"}
data: {"type": "token", "content": " has"}
data: {"type": "done", "cached": false}
```

Event types:

| Type | Fields | When |
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

---

### `POST /v1/ingest`

Sanity CMS webhook — re-ingests all Sanity content and invalidates
the response cache when portfolio content changes.

**Response:**

```json
{
  "status": "ok",
  "chunks_ingested": 12,
}
```

**Rate limit:** 10 requests/minute per IP.

---

## Sanity Webhook Setup

The ingest endpoint is protected by HMAC-SHA256 signature verification.
Only requests signed with your webhook secret are accepted.

### Step 1 — Generate a webhook secret

```bash
openssl rand -hex 32
```

Copy the output — this is your `INGEST_WEBHOOK_SECRET`.

### Step 2 — Add to environment variables

In `.env.prod` and Railway dashboard:

```bash
INGEST_WEBHOOK_SECRET=your-generated-secret-here
```

### Step 3 — Configure Sanity webhook

1. Go to [sanity.io/manage](https://sanity.io/manage) → your project → API → Webhooks
2. Click **Add webhook**
3. Fill in:
   - **Name:** Portfolio content sync
   - **URL:** `https://your-deployment.up.railway.app/v1/ingest`
   - **Trigger on:** Create, Update, Delete
   - **Filter:** `_type == "project" || _type == "testimonial"`
   - **Secret:** paste your `INGEST_WEBHOOK_SECRET`
4. Save

Every time you publish or delete a project or testimonial in Sanity Studio, the webhook fires — re-ingesting the content and clearing stale cache entries automatically.

### How verification works

Sanity signs the request body with HMAC-SHA256 using your shared secret and sends the signature in the `x-sanity-webhook-signature` header. The API verifies this signature before processing — ensuring only Sanity can trigger re-ingestion.

If `INGEST_WEBHOOK_SECRET` is empty in config, signature verification is skipped. Never deploy without a secret set.

---

## Cache Invalidation

The response cache is cleared automatically whenever content is re-ingested:

| Trigger | Action |
|---|---|
| `make ingest` (any source) | Cache cleared before new chunks stored |
| Sanity webhook fires | Cache cleared, then Sanity re-ingested |
| TTL expires | Entries older than `CACHE_TTL_DAYS` (default 7) ignored automatically |

This means users always get fresh answers after you update your portfolio or re-ingest your resume.

---

## CORS

The API allows requests from:

- `http://localhost:3000` (Next.js dev)
- `http://localhost:5173` (Vite dev)
- `https://chitrankagnihotri.com` (production portfolio)

Add origins to `API_ALLOWED_ORIGINS` in `config.py` if needed.

---

## Rate Limiting

In-memory rate limiting via slowapi. Limits reset on server restart.

| Endpoint | Limit |
|---|---|
| `POST /v1/chat` | 30/minute |
| `POST /v1/ingest` | 10/minute |

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