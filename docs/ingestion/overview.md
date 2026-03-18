# Ingestion Pipeline

The ingestion pipeline loads documents from three sources, chunks them,
embeds via Voyage AI, and stores in Supabase pgvector.

---

## Overview

```
data/resume.pdf          → pdf_loader.py     → section-aware chunks (6)
Sanity CMS API           → sanity_loader.py  → plain text documents (12)
data/linkedin/ CSVs      → linkedin_loader.py → formatted plain text (4)
                                    ↓
                             chunker.py (500 words, 50 overlap)
                                    ↓
                          embedder.py (Voyage AI voyage-3-lite)
                                    ↓
                         knowledge_chunks table (22 total chunks)
```

---

## Running Ingestion

```bash
make ingest
```

Opens an interactive menu to select sources. Select one, two, or all three — they run sequentially in fixed order: resume → sanity → linkedin.

Or run directly:

```bash
uv run python -m src.main ingest --source resume
uv run python -m src.main ingest --source resume sanity linkedin
```

---

## Sources

### Resume PDF

**File:** `data/resume.pdf`

Uses section-aware chunking — splits on known section headers rather than word count. Each chunk answers a distinct type of question:

| Chunk                          | source_id                        | Answers                              |
|--------------------------------|----------------------------------|--------------------------------------|
| Introduction                   | `resume-introduction`            | Contact info, name                   |
| Summary                        | `resume-summary`                 | Background, years of experience      |
| Professional Experience        | `resume-professional-experience` | Roles, companies, achievements       |
| Employment History             | `resume-employment-history`      | Consultancy history                  |
| Education                      | `resume-education`               | Degree, university                   |
| Technical Skills               | `resume-technical-skills`        | Languages, frameworks, tools         |

### Sanity CMS

**Fetched from:** Sanity HTTP API via GROQ queries

Fetches `Project` and `Testimonial` document types. Formatted as plain text — no JSON, no brackets — to minimise LLM token usage.

Fields ingested per Project: title, role, company, overview, vision, technologies, contribution, liveUrl, githubUrl.

Fields ingested per Testimonial: author, role, quote.

Images excluded — not useful for text retrieval.

### LinkedIn

**Files:** `data/linkedin/` directory

| File                  | Content                                 | Documents              |
|-----------------------|-----------------------------------------|------------------------|
| `Recommendations.csv` | Written recommendations from colleagues | One per recommendation |
| `Positions.csv`       | Work history                            | One per role           |
| `Skills.csv`          | Endorsed skills                         | One grouped document   |

Missing CSVs are skipped with a warning — partial exports handled gracefully.

---

## Idempotency

Every ingest function clears existing chunks for that source before re-ingesting:

```sql
DELETE FROM knowledge_chunks WHERE source = 'resume'
```

Re-running never creates duplicates. Each source is independent — re-ingesting resume does not affect Sanity or LinkedIn chunks.

---

## Chunking Strategy

### Section-aware chunking — Resume

Resume text is split at known section headers. Resumes are short (~700 words) — word-count chunking would produce 1-2 large chunks always returned regardless of the question. Section chunking produces 6 focused chunks with high retrieval precision.

### Word-count chunking — Sanity + LinkedIn

500 words per chunk with 50-word overlap. The overlap ensures context continuity at chunk boundaries.

---

## Embeddings

All text embedded via Voyage AI `voyage-3-lite`:

- 512 dimensions
- `document` input type for chunks stored in knowledge_chunks
- `query` input type for user questions at retrieval time
- Asymmetric embedding — different input types improve retrieval accuracy
- Batched in groups of 128 — Voyage AI maximum batch size
- Free tier: 200M tokens/month

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)