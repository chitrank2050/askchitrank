# Database Setup

Ask Chitrank uses Supabase PostgreSQL with the pgvector extension for vector similarity search.

---

## Supabase Setup

### 1. Create a Supabase project

Go to [supabase.com](https://supabase.com) → New Project.

Recommended region: Asia Pacific (Singapore) — closest to India.

### 2. Enable pgvector extension

Go to **SQL Editor** and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This enables the `VECTOR` column type used for storing embeddings.

### 3. Get connection strings

Go to **Settings** → **Database** → **Connection string**.

```bash
# Async — FastAPI runtime
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres

# Sync — Alembic migrations only
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
```

---

## Running Migrations

```bash
# Apply all pending migrations
make db-migrate

# Create a new migration after model changes
make db-migration

# Roll back the last migration
make db-rollback
```

---

## Tables

### `knowledge_chunks`

Stores embedded text chunks from all ingestion sources.

| Column       | Type        | Description                                               |
|--------------|-------------|-----------------------------------------------------------|
| `id`         | UUID        | Primary key                                               |
| `source`     | VARCHAR     | `resume`, `sanity`, or `linkedin`                         |
| `source_id`  | VARCHAR     | Section name, Sanity doc ID, or CSV row identifier        |
| `content`    | TEXT        | Raw chunk text shown to LLM as context                    |
| `embedding`  | VECTOR(512) | Voyage AI voyage-3-lite embedding                         |
| `chunk_index`| INTEGER     | Position in source document                               |
| `created_at` | TIMESTAMPTZ | Ingestion timestamp                                       |
| `updated_at` | TIMESTAMPTZ | Last update timestamp                                     |

### `response_cache`

Caches question→response pairs to reduce LLM API costs.

| Column               | Type        | Description                               |
|----------------------|-------------|-------------------------------------------|
| `id`                 | UUID        | Primary key                               |
| `question`           | TEXT        | Original user question                    |
| `question_embedding` | VECTOR(512) | For similarity lookup                     |
| `response`           | TEXT        | Cached LLM response                       |
| `source_chunk_ids`   | TEXT        | JSON array of chunk UUIDs used            |
| `hit_count`          | INTEGER     | Times this cache entry was served         |
| `created_at`         | TIMESTAMPTZ | Cache entry creation time                 |
| `invalidated_at`     | TIMESTAMPTZ | Null = valid. Set on webhook invalidation |

### `conversations`

Stores conversation history per browser session.

| Column           | Type            | Description                |
|------------------|-----------------|----------------------------|
| `id`             | UUID            | Primary key                |
| `session_id`     | VARCHAR         | Browser session identifier |
| `role`           | VARCHAR         | `user` or `assistant`      |
| `content`        | TEXT            | Message text               |
| `created_at`     | TIMESTAMPTZ     | Message timestamp          |

---

## Supabase Free Tier Behaviour

Supabase free tier pauses the database after 1 week of inactivity. The first request after a pause will be slow (~2-3 seconds) as the database wakes up.

This is handled by `pool_pre_ping=True` in `connection.py` — subsequent requests are fast once the database is awake.

---

## Alembic Version Table

The migration version table is named `alembic_version_askchitrank` — separate from any other project using the same Supabase database.

Configured in `alembic.ini`:

```ini
version_table = alembic_version_askchitrank
```

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)