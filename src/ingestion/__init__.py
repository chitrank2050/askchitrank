"""
Ingestion pipeline package.

Loads documents from three sources:
    resume   — PDF fetched from data/resume.pdf
    sanity   — Projects and Testimonials from Sanity CMS API
    linkedin — CSV exported from LinkedIn at data/linkedin/*.csv

Sources are first normalized into retrieval-friendly evidence documents.
Long documents then pass through a block-aware semantic chunker that
preserves headings, labeled fields, and repeated prefixes before
embeddings are stored in the knowledge_chunks table.

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
