# Setup

This guide covers setting up Ask Chitrank for local development.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
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

## 2. Create Virtual Environment

```bash
make init
# If above fails, run below commands
uv venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
make install
# If above fails, run below commands
uv sync --all-groups
```

---

## 4. Set Up Environment

```bash
cp .env.example .env.dev
```

Open `.env.dev` and fill in:

```bash
# Required — get from console.groq.com (free, no credit card)
GROQ_API_KEY=your-groq-api-key

# Required — get from voyageai.com (free tier)
VOYAGE_API_KEY=your-voyage-api-key

# Required — get from Supabase dashboard → Settings → Database
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Required — get from sanity.io/manage
SANITY_PROJECT_ID=your-project-id
SANITY_API_TOKEN=your-api-token
```

---

## 5. Set Up Database

See [Database Setup](database.md) for full instructions.

Quick start:

```bash
make db-migrate
```

---

## 6. Ingest Data

```bash
# Ingest resume
make ingest-resume

# Ingest Sanity CMS
make ingest-sanity
```

---

## 7. Start the API

```bash
make api
# Open http://localhost:8000/docs
```

---

## API Keys

| Service | URL | Cost |
|---|---|---|
| Groq | [console.groq.com](https://console.groq.com) | Free tier, no card |
| Voyage AI | [voyageai.com](https://www.voyageai.com) | 200M tokens/month free |
| Supabase | [supabase.com](https://supabase.com) | Free tier |
| Anthropic (future) | [console.anthropic.com](https://console.anthropic.com) | $5 credit on signup |