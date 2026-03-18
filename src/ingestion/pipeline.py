"""src/ingestion/pipeline.py

Ingestion pipeline orchestration.

Coordinates loading, chunking, embedding, and storing
documents from all sources into the knowledge_chunks table.

Ingestion is idempotent — re-running clears existing chunks
for the source and re-ingests fresh data.

Responsibility: orchestrate ingestion. Nothing else.
Does NOT: define loading, chunking, or embedding logic.

Typical usage:
    from src.ingestion.pipeline import ingest_resume, ingest_sanity

    await ingest_resume("data/resume.pdf", db)
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
    chunks: Sequence[dict],
    embeddings: Sequence[Sequence[float]],
    db: AsyncSession,
) -> None:
    """Store chunks and their embeddings in the database.

    Args:
        chunks: List of chunk dicts with content, source, source_id, chunk_index.
        embeddings: List of embedding vectors matching chunks order.
        db: Async database session.
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


async def ingest_resume(path: str | Path, db: AsyncSession) -> int:
    """Ingest a resume PDF into the knowledge base.

    Clears existing resume chunks before re-ingesting.
    Idempotent — safe to run multiple times.

    Args:
        path: Path to the resume PDF file.
        db: Async database session.

    Returns:
        Number of chunks stored.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
    """
    logger.info(f"Ingesting resume: {path}")

    # Clear existing resume chunks — idempotent re-ingestion
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == "resume"))
    await db.commit()
    logger.info("Cleared existing resume chunks")

    # Load and chunk
    text = await load_pdf(path)
    chunks = chunk_document(text, source="resume", source_id=str(path))

    if not chunks:
        logger.warning("No chunks produced from resume PDF")
        return 0

    # Embed
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    # Store
    await _store_chunks(chunks, embeddings, db)
    logger.success(f"Resume ingested — {len(chunks)} chunks stored")
    return len(chunks)


async def ingest_sanity(db: AsyncSession) -> int:
    """Ingest all Sanity CMS documents into the knowledge base.

    Clears existing Sanity chunks before re-ingesting.
    Idempotent — safe to run multiple times.

    Args:
        db: Async database session.

    Returns:
        Number of chunks stored.
    """
    logger.info("Ingesting Sanity CMS documents")

    # Clear existing Sanity chunks
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == "sanity"))
    await db.commit()
    logger.info("Cleared existing Sanity chunks")

    # Load documents
    documents = await load_sanity_documents()

    if not documents:
        logger.warning("No documents fetched from Sanity CMS")
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

    # Embed all chunks
    texts = [c["content"] for c in all_chunks]
    embeddings = await embed_texts(texts)

    # Store
    await _store_chunks(all_chunks, embeddings, db)
    logger.success(f"Sanity ingested — {len(all_chunks)} chunks stored")
    return len(all_chunks)
