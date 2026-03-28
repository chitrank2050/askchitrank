# Ingestion Pipeline

The ingestion pipeline loads source content, turns it into retrieval-friendly evidence documents, embeds those documents, and stores them in pgvector.

---

## Overview

```
data/resume.pdf            → pdf_loader.py       → section-aware resume documents
Sanity CMS API             → sanity_loader.py    → project/testimonial evidence docs
data/linkedin/ CSVs        → linkedin_loader.py  → profile/recommendation evidence docs
                                       ↓
                 chunker.py → block-aware semantic grouping + chunk packing
                                       ↓
                            embedder.py (Voyage AI or local providers)
                                       ↓
                               knowledge_chunks table
```

Chunk counts are no longer treated as fixed documentation numbers because they vary with source content and with how many evidence documents are emitted per record.

---

## Running Ingestion

```bash
make ingest
```

Or run directly:

```bash
uv run python -m src.main ingest --source resume
uv run python -m src.main ingest --source resume sanity linkedin
```

Sources still run sequentially in fixed order: `resume → sanity → linkedin`.

---

## Sources

### Resume PDF

**File:** `data/resume.pdf`

The resume uses section-aware chunking because resumes are short and semantically dense. Each section tends to answer a different class of question.

Typical sections:

- introduction
- summary
- professional experience
- employment history
- education
- technical skills

### Sanity CMS

**Fetched from:** Sanity HTTP API via GROQ queries

Projects are no longer represented only as one broad text block. They are decomposed into retrieval-friendly evidence documents such as:

- project overview
- project contributions
- project links

Testimonials are also given their own evidence documents with explicit testimonial labelling.

This change improves precision for questions about:

- technologies
- responsibilities
- impact
- portfolio links
- colleague feedback

### LinkedIn

**Files:** `data/linkedin/Profile.csv` and `data/linkedin/Recommendations_Received.csv`

The LinkedIn loader currently uses:

- `Profile.csv`
- `Recommendations_Received.csv`

From those files it emits compact evidence documents such as:

- profile summary
- profile links
- one recommendation document per visible recommendation

Missing CSVs are still skipped with warnings so partial exports remain usable.

---

## Idempotency

Each ingest function clears existing chunks for the relevant source before storing the new ones:

```sql
DELETE FROM knowledge_chunks WHERE source = 'resume'
```

Re-running ingestion never creates duplicates. Cache entries are invalidated before new content is stored so stale answers are not served.

---

## Chunking Strategy

### Section-aware chunking — Resume

The resume is split by known section headers because that gives much better retrieval precision than treating the whole document as one long chunk.

### Structured evidence documents — Sanity + LinkedIn

Sanity and LinkedIn sources now do most of their quality work before generic chunking. They first create smaller, purpose-built evidence documents.

This is the main retrieval ROI improvement because it produces:

- tighter semantic units
- cleaner technology and role matching
- less cross-topic noise in search results

### Block-aware semantic chunking — Safety net

`chunker.py` now acts as a smarter second-stage chunker:

- it preserves paragraph and line-group boundaries when possible
- it semantically groups adjacent related blocks before final packing
- it splits early when labeled blocks clearly change topic
- it repeats stable prefixes like `Resume Section: ...` or `Project: ...` on derived chunks

Word overlap still exists, but the default behavior is no longer a plain word slicer.

---

## Embeddings

Production ingestion uses Voyage AI `voyage-3-lite` by default:

- 512 dimensions
- `document` input type for stored chunks
- batched up to 128 texts per request

In `DEV_MODE`, the embedder switches to a deterministic local implementation so local development does not spend tokens. Outside `DEV_MODE`, you can also opt into the local `sentence-transformers` provider for fully local embeddings.

---

## Why These Changes Were High ROI

The ingestion layer is where retrieval quality starts. Better source representation improved RAG quality more cheaply than swapping providers because:

- the embedding model now sees cleaner evidence
- retrieval has more precise units to select from
- the change adds no extra provider calls

---

Developed by [Chitrank Agnihotri](https://www.chitrankagnihotri.com)
