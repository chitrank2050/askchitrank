"""
Ingestion pipeline orchestration.

Coordinates loading, chunking, embedding, and storing
documents from all sources into the knowledge_chunks table.

Ingestion is idempotent — re-running clears existing chunks
for the source and re-ingests fresh data. Safe to run
multiple times without creating duplicates.

Responsibility: orchestrate ingestion. Nothing else.
Does NOT: define loading, chunking, or embedding logic.

Typical usage:
    from src.ingestion.pipeline import ingest_resume, ingest_sanity

    await ingest_resume("https://chitrankagnihotri.com/resume.pdf", db)
    await ingest_sanity(db)
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


async def _store_chunks(
    chunks: list[dict],
    embeddings: Sequence[Sequence[float]],
    db: AsyncSession,
) -> None:
    """Store document chunks and their embeddings in the database.

    Args:
        chunks: List of chunk dicts with content, source,
            source_id, and chunk_index keys.
        embeddings: List of embedding vectors in the same
            order as chunks.
        db: Active async database session.
    """
    for chunk, embedding in zip(chunks, embeddings, strict=True):
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


async def ingest_resume(source: str | Path, db: AsyncSession) -> int:
    """Ingest a resume PDF into the knowledge base.

    Clears all existing resume chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        source: HTTPS URL or local path to the resume PDF.
        db: Active async database session.

    Returns:
        Number of chunks stored.

    Raises:
        FileNotFoundError: If local path does not exist.
        httpx.HTTPError: If URL fetch fails.
    """
    logger.info(f"Starting resume ingestion from: {source}")

    # Clear existing resume chunks before re-ingesting
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == "resume"))
    await db.commit()
    logger.info("Cleared existing resume chunks")

    # Load text from PDF
    text = await load_pdf(source)
    chunks = chunk_document(text, source="resume", source_id=str(source))

    if not chunks:
        logger.warning("No chunks produced from resume PDF — check file content")
        return 0

    # Embed all chunks
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    # Store chunks + embeddings
    await _store_chunks(chunks, embeddings, db)
    logger.success(f"Resume ingestion complete — {len(chunks)} chunks stored")
    return len(chunks)


async def ingest_sanity(db: AsyncSession) -> int:
    """Ingest all Sanity CMS documents into the knowledge base.

    Clears all existing Sanity chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        db: Active async database session.

    Returns:
        Number of chunks stored.

    Raises:
        httpx.HTTPError: If Sanity API requests fail.
    """
    logger.info("Starting Sanity CMS ingestion")

    # Clear existing Sanity chunks before re-ingesting
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == "sanity"))
    await db.commit()
    logger.info("Cleared existing Sanity chunks")

    # Load all documents from Sanity CMS
    documents = await load_sanity_documents()

    if not documents:
        logger.warning("No documents fetched from Sanity CMS — check credentials")
        return 0

    # Chunk all documents
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(
            doc["text"],
            source=doc["source"],
            source_id=doc["source_id"],
        )
        all_chunks.extend(chunks)

    logger.info(f"Produced {len(all_chunks)} chunks from {len(documents)} documents")

    # Embed all chunks in batches
    texts = [c["content"] for c in all_chunks]
    embeddings = await embed_texts(texts)

    # Store chunks + embeddings
    await _store_chunks(all_chunks, embeddings, db)
    logger.success(f"Sanity ingestion complete — {len(all_chunks)} chunks stored")
    return len(all_chunks)
