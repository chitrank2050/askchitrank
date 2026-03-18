"""
Ingestion pipeline package.

Loads documents from resume PDF and Sanity CMS,
chunks them into 500-word segments with 50-word overlap,
embeds via Voyage AI voyage-3-lite, and stores in
the knowledge_chunks table.

Typical usage:
    from src.ingestion import ingest_resume, ingest_sanity

    await ingest_resume("https://chitrankagnihotri.com/resume.pdf", db)
    await ingest_sanity(db)
"""

from src.ingestion.pipeline import ingest_resume, ingest_sanity

__all__ = ["ingest_resume", "ingest_sanity"]
