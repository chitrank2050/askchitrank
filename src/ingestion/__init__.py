"""
Ingestion pipeline package.

Loads documents from three sources:
    resume   — PDF fetched from data/resume.pdf
    sanity   — Projects and Testimonials from Sanity CMS API
    linkedin — CSV exported from LinkedIn at data/linkedin/*.csv

Each source is chunked into 500-word segments with 50-word overlap,
embedded via Voyage AI voyage-3-lite (512 dimensions), and stored
in the knowledge_chunks table for vector similarity search.

Typical usage:
    from src.ingestion import ingest_resume, ingest_sanity, ingest_linkedin

    await ingest_resume("https://chitrankagnihotri.com/resume.pdf", db)
    await ingest_sanity(db)
    await ingest_linkedin(db)
"""

from .pipeline import ingest_linkedin, ingest_resume, ingest_sanity

__all__ = [
    "ingest_linkedin",
    "ingest_resume",
    "ingest_sanity",
]
