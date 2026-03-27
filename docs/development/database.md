# Database Setup

Ask Chitrank uses PostgreSQL with the pgvector extension for vector similarity search.
For local development, use a local PostgreSQL instance. For production, Supabase
is a good hosted option.

---

## Local Development Setup

Create a local database first:

```sql
CREATE DATABASE askchitrank;
```

Then configure your local env file:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/askchitrank
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5432/askchitrank
```

Enable `pgvector` in that database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Production Setup With Supabase

### 1. Create a Supabase project

Go to [supabase.com](https://supabase.com) and create a new project.

### 2. Enable pgvector

Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Get connection strings

Store these in your production env file, not your local dev env:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

---

## Running Migrations

```bash
make db-migrate
make db-migration
make db-rollback
```

---

## Tables

### `knowledge_chunks`

Stores retrieval-ready evidence chunks from all ingestion sources.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | primary key |
| `source` | VARCHAR | `resume`, `sanity`, `linkedin`, or `testimonial` |
| `source_id` | VARCHAR | source identifier, sometimes with fragment suffixes like `#overview` or `#links` |
| `content` | TEXT | retrieval-ready evidence text shown to the LLM |
| `embedding` | VECTOR(512) | embedding vector |
| `chunk_index` | INTEGER | position within the source document |
| `created_at` | TIMESTAMPTZ | ingestion timestamp |
| `updated_at` | TIMESTAMPTZ | last update timestamp |

### `response_cache`

Caches semantically similar question → response pairs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | primary key |
| `question` | TEXT | original user question |
| `question_embedding` | VECTOR(512) | embedding for similarity lookup |
| `response` | TEXT | cached answer |
| `source_chunk_ids` | TEXT | JSON array of chunk UUIDs used |
| `hit_count` | INTEGER | number of cache hits |
| `created_at` | TIMESTAMPTZ | cache creation time |
| `invalidated_at` | TIMESTAMPTZ | `NULL` means active |

### `conversations`

Stores multi-turn history per browser session.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | primary key |
| `session_id` | VARCHAR | browser session identifier |
| `role` | VARCHAR | `user` or `assistant` |
| `content` | TEXT | message text |
| `created_at` | TIMESTAMPTZ | timestamp |

---

## Free Tier Behaviour

Supabase free tier can pause the database after inactivity. The first request after a pause may be slower while the database wakes up.

`pool_pre_ping=True` is used to help connection reuse behave cleanly after wake-up.

---

## Connection Pooling (IPv4 Poolers)

When deploying to PaaS platforms (like Render, Fly.io, or Railway), you should use Supabase's built-in connection pooler (PGBouncer or Supavisor) rather than the direct database port (5432).

Direct connections are limited and can fluctuate as the database pauses. The pooler manages thousands of concurrent connections and is more robust for serverless or ephemeral environments.

| Type | Host | Port | SSL |
|------|------|------|-----|
| Direct | `db.[REF].supabase.co` | `5432` | Optional |
| Pooler (Session) | `db.[REF].supabase.co` | `6543` | Required |
| Pooler (Transaction)| `db.[REF].supabase.co` | `6543` | Required |

Note: If your PaaS uses an IPv4-only network but your Supabase hostname resolves only to IPv6, you **must** use the pooler connection string and append `?sslmode=require` to the `DATABASE_URL`.

---

## DEV_MODE Note

The database is optional only for chat-only local development in `DEV_MODE`.

If you want:

- persistent conversations
- semantic cache
- ingestion-backed retrieval

you still need the database configured.

---

## Alembic Version Table

The migration version table is `alembic_version_askchitrank`.

```ini
version_table = alembic_version_askchitrank
```

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
