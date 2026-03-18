# Setup

This guide covers setting up Ask Chitrank for local development.

---

## Prerequisites

| Tool   | Version   | Install                                    |
|--------|-----------|--------------------------------------------|
| Python | 3.12+     | [python.org](https://www.python.org)       |
| uv     | latest    | `brew install uv`                          |
| Git    | latest    | [git-scm.com](https://git-scm.com)         |

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
```

---

## 3. Install Dependencies

```bash
make install
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

```bash
make db-migrate
```

---

## 6. Prepare Data Sources

**Resume:**

Place your resume PDF at `data/resume.pdf`.

**LinkedIn:**

Export your LinkedIn data: LinkedIn → Settings & Privacy → Data Privacy → Get a copy of your data → Request archive.

Extract the archive and place these CSVs in `data/linkedin/`:
- `Recommendations.csv`
- `Positions.csv`
- `Skills.csv`

**Sanity CMS:**

No manual steps needed — fetched automatically via API during ingestion.

---

## 7. Ingest Data

```bash
make ingest
```

Opens an interactive menu to select which sources to ingest. Select all three on first run.

---

## 8. Start the API

```bash
make api
```

---

## API Keys

| Service | URL | Cost |
|---|---|---|
| Groq | [console.groq.com](https://console.groq.com) | Free tier, no card |
| Voyage AI | [voyageai.com](https://www.voyageai.com) | 200M tokens/month free |
| Supabase | [supabase.com](https://supabase.com) | Free tier |
| Anthropic (future) | [console.anthropic.com](https://console.anthropic.com) | $5 credit on signup |

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)