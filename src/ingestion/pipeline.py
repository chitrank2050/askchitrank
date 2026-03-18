"""
Ingestion pipeline orchestration.

Coordinates loading, chunking, embedding, and storing
documents from all sources into the knowledge_chunks table.

Ingestion is idempotent — re-running clears existing chunks
for the source and re-ingests fresh data. Safe to run
multiple times without creating duplicates.

Sources:
    resume   — PDF fetched from RESUME_URL in config
    sanity   — Projects and Testimonials from Sanity CMS API
    linkedin — PDF exported from LinkedIn, stored at data/linkedin.pdf

Responsibility: orchestrate ingestion. Nothing else.
Does NOT: define loading, chunking, or embedding logic.

Typical usage:
    from src.ingestion.pipeline import ingest_resume, ingest_sanity, ingest_linkedin

    await ingest_resume("https://chitrankagnihotri.com/resume.pdf", db)
    await ingest_sanity(db)
    await ingest_linkedin(db)
"""

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import logger
from src.db.models import KnowledgeChunk
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_texts
from src.ingestion.pdf_loader import load_pdf
from src.ingestion.sanity_loader import load_sanity_documents
from utils import PROJECT_ROOT


async def _clear_source(source: str, db: AsyncSession) -> None:
    """Delete all existing chunks for a given source before re-ingesting.

    Called at the start of each ingest function to ensure idempotency.
    Without this, re-running ingestion would create duplicate chunks.

    Args:
        source: Source identifier to clear — 'resume', 'sanity', or 'linkedin'.
        db: Active async database session.
    """
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == source))
    await db.commit()
    logger.info(f"Cleared existing '{source}' chunks")


async def _store_chunks(
    chunks: list[dict],
    embeddings: Sequence[Sequence[float]],
    db: AsyncSession,
) -> None:
    """Store document chunks and their embeddings in the database.

    Pairs each chunk with its corresponding embedding vector and
    creates a KnowledgeChunk ORM instance for each pair.

    Args:
        chunks: List of chunk dicts with content, source,
            source_id, and chunk_index keys.
        embeddings: List of embedding vectors in the same
            order as chunks. Must match len(chunks).
        db: Active async database session.
    """
    for chunk, embedding in zip(chunks, embeddings, strict=False):
        db.add(
            KnowledgeChunk(
                source=chunk["source"],
                source_id=chunk["source_id"],
                content=chunk["content"],
                embedding=embedding,
                chunk_index=chunk["chunk_index"],
            )
        )
    await db.commit()
    logger.info(f"Stored {len(chunks)} chunks in knowledge_chunks")


async def ingest_linkedin(db: AsyncSession) -> int:
    """Ingest LinkedIn profile data into the knowledge base.

    Reads CSV files exported from LinkedIn (Recommendations,
    Positions, Skills) from data/linkedin/ directory.

    LinkedIn export instructions:
        LinkedIn → Settings & Privacy → Data Privacy →
        Get a copy of your data → Request archive →
        Place CSVs in data/linkedin/

    Clears all existing LinkedIn chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        db: Active async database session.

    Returns:
        Number of chunks stored. 0 if no documents loaded.

    Raises:
        FileNotFoundError: If data/linkedin/ directory does not exist.
    """
    from src.ingestion.linkedin_loader import load_linkedin_documents

    linkedin_dir = PROJECT_ROOT / "data" / "linkedin"

    if not linkedin_dir.exists():
        raise FileNotFoundError(
            f"LinkedIn data directory not found at {linkedin_dir}.\n"
            "Export your LinkedIn data and place CSVs in data/linkedin/.\n"
            "LinkedIn → Settings & Privacy → Data Privacy → "
            "Get a copy of your data → Request archive."
        )

    logger.info(f"Starting LinkedIn ingestion from: {linkedin_dir}")

    await _clear_source("linkedin", db)

    documents = await load_linkedin_documents()

    if not documents:
        logger.warning(
            "No LinkedIn documents loaded — check CSV files in data/linkedin/"
        )
        return 0

    all_chunks = []
    for doc in documents:
        chunks = chunk_document(
            doc["text"],
            source=doc["source"],
            source_id=doc["source_id"],
        )
        all_chunks.extend(chunks)

    logger.info(
        f"Produced {len(all_chunks)} chunks from {len(documents)} LinkedIn documents"
    )

    texts = [c["content"] for c in all_chunks]
    embeddings = await embed_texts(texts)

    await _store_chunks(all_chunks, embeddings, db)
    logger.success(f"LinkedIn ingestion complete — {len(all_chunks)} chunks stored")
    return len(all_chunks)


async def ingest_resume(source: str | Path, db: AsyncSession) -> int:
    """Ingest a resume PDF into the knowledge base.

    Fetches the PDF from a remote URL or local path, extracts text,
    chunks it into 500-word segments, embeds via Voyage AI, and
    stores in knowledge_chunks.

    Clears all existing resume chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        source: HTTPS URL or local path to the resume PDF.
            Defaults to settings.RESUME_URL when called via main.py.
        db: Active async database session.

    Returns:
        Number of chunks stored. 0 if PDF produced no content.

    Raises:
        FileNotFoundError: If local path does not exist.
        httpx.HTTPError: If URL fetch fails or returns non-200.
        pypdf.errors.PdfReadError: If file is not a valid PDF.

    Example:
        >>> count = await ingest_resume("https://example.com/resume.pdf", db)
        >>> print(f"{count} chunks stored")
    """
    logger.info(f"Starting resume ingestion from: {source}")

    await _clear_source("resume", db)

    # Load and extract text from PDF
    text = await load_pdf(source)
    chunks = chunk_document(text, source="resume", source_id=str(source))

    if not chunks:
        logger.warning("No chunks produced from resume PDF — check file content")
        return 0

    # Embed all chunks via Voyage AI
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    await _store_chunks(chunks, embeddings, db)
    logger.success(f"Resume ingestion complete — {len(chunks)} chunks stored")
    return len(chunks)


async def ingest_sanity(db: AsyncSession) -> int:
    """Ingest all Sanity CMS documents into the knowledge base.

    Fetches Project and Testimonial documents via the Sanity HTTP API,
    formats each as plain text, chunks, embeds, and stores.

    Clears all existing Sanity chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        db: Active async database session.

    Returns:
        Number of chunks stored. 0 if no documents fetched.

    Raises:
        httpx.HTTPError: If Sanity API requests fail.

    Example:
        >>> count = await ingest_sanity(db)
        >>> print(f"{count} chunks stored")
    """
    logger.info("Starting Sanity CMS ingestion")

    await _clear_source("sanity", db)

    # Fetch all documents from Sanity CMS
    documents = await load_sanity_documents()

    if not documents:
        logger.warning("No documents fetched from Sanity CMS — check credentials")
        return 0

    # Chunk all documents into 500-word segments
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(
            doc["text"],
            source=doc["source"],
            source_id=doc["source_id"],
        )
        all_chunks.extend(chunks)

    logger.info(f"Produced {len(all_chunks)} chunks from {len(documents)} documents")

    # Embed all chunks in batches via Voyage AI
    texts = [c["content"] for c in all_chunks]
    embeddings = await embed_texts(texts)

    await _store_chunks(all_chunks, embeddings, db)
    logger.success(f"Sanity ingestion complete — {len(all_chunks)} chunks stored")
    return len(all_chunks)
