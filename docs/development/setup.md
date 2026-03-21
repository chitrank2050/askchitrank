# Setup

This guide covers both full production-like setup and low-cost local development.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org) |
| uv | latest | `brew install uv` |
| Git | latest | [git-scm.com](https://git-scm.com) |

---

## 1. Clone the Repository

```bash
git clone https://github.com/chitrank2050/askchitrank.git
cd askchitrank
```

---

## 2. Create the Environment

```bash
make init
make install
cp .env.example .env.dev
```

---

## 3. Choose a Local Mode

### Option A — Token-free local development

If you want to work on the API, prompt flow, streaming, or frontend integration without spending Groq or Voyage quota:

```bash
API_TOKEN=dev-token
DEV_MODE=true
```

Optional:

```bash
CONTACT_EMAIL=hello@example.dev
```

In this mode:

- Groq calls are skipped
- Voyage calls are skipped
- chat can run without a database
- fictional seeded data is used for local responses

This is the recommended default for day-to-day local iteration.

### Option B — Full provider-backed development

If you want to exercise the full production-style pipeline, fill in:

```bash
GROQ_API_KEY=your-groq-api-key
VOYAGE_API_KEY=your-voyage-api-key
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_KEY=your-supabase-anon-key
SANITY_PROJECT_ID=your-project-id
SANITY_API_TOKEN=your-api-token
API_TOKEN=your-generated-token
DEV_MODE=false
```

---

## 4. Database Setup

For the full pipeline, follow [Database Setup](database.md) and run:

```bash
make db-migrate
```

If you stay in token-free `DEV_MODE`, chat-only API work does not require the database.

---

## 5. Prepare Data Sources

### Resume

Place your resume PDF at `data/resume.pdf`.

### LinkedIn

Export your LinkedIn data and place these CSVs in `data/linkedin/`:

- `Profile.csv`
- `Recommendations_Received.csv`

### Sanity CMS

No manual content export is needed. Data is fetched via the Sanity API during ingestion.

---

## 6. Ingest Data

```bash
make ingest
```

Notes:

- In full mode, this stores real embeddings in the database.
- In `DEV_MODE`, ingestion uses fictional seeded source content.
- In `DEV_MODE` without a configured database, ingestion is skipped because there is nowhere to persist chunks.

---

## 7. Start the API

```bash
make api
```

If `DEV_MODE=true`, the API can start and serve fictional seeded chat responses even without database credentials.

---

## Service Setup

| Service | URL | Cost |
|---------|-----|------|
| Groq | [console.groq.com](https://console.groq.com) | free tier |
| Voyage AI | [voyageai.com](https://www.voyageai.com) | generous free tier |
| Supabase | [supabase.com](https://supabase.com) | free tier |
| Sanity | [sanity.io/manage](https://sanity.io/manage) | depends on workspace plan |

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
