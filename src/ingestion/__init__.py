"""src/ingestion

Ingestion pipeline package.

Loads documents from resume PDF and Sanity CMS,
chunks them into 500-word segments, embeds via Voyage AI,
and stores in the knowledge_chunks table.
"""

from src.ingestion.pipeline import ingest_resume, ingest_sanity

__all__ = ["ingest_resume", "ingest_sanity"]
