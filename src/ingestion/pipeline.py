"""
Ingestion pipeline orchestration.

Coordinates loading, chunking, embedding, and storing
documents from all sources into the knowledge_chunks table.

Ingestion is idempotent — re-running clears existing chunks
for the source and re-ingests fresh data. Safe to run
multiple times without creating duplicates.

Sources:
    resume   — PDF fetched from data/resume.pdf
    sanity   — Projects and Testimonials from Sanity CMS API
    linkedin — CSV exported from LinkedIn at data/linkedin/*.csv

Responsibility: orchestrate ingestion. Nothing else.
Does NOT: define loading, chunking, or embedding logic.

Typical usage:
    from src.ingestion.pipeline import ingest_resume, ingest_sanity, ingest_linkedin

    await ingest_resume(db)
    await ingest_sanity(db)
    await ingest_linkedin(db)
"""

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger
from src.db.models import KnowledgeChunk
from src.dev.seed_data import SEED_RESUME_TEXT
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_texts
from src.ingestion.sanity_loader import load_sanity_documents
from src.retrieval import invalidate_cache
from src.utils.paths import get_data_path

from .pdf_loader import load_pdf_from_data


async def _clear_source(source: list[str], db: AsyncSession) -> None:
    """Delete all existing chunks for a given source before re-ingesting.

    Called at the start of each ingest function to ensure idempotency.
    Without this, re-running ingestion would create duplicate chunks.

    Args:
        source: Source identifier to clear — 'resume', 'sanity', or 'linkedin'.
        db: Active async database session.
    """

    # Invalidate cache first — old answers are stale immediately
    invalidated = await invalidate_cache(db)
    logger.info(f"Invalidated {invalidated} cache entries")

    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(source)))
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


async def _download_pdf(url: str, dest: Path) -> None:
    """Download a PDF from a URL to a local file.

    Creates the parent directory if it does not exist.

    Args:
        url: HTTPS URL to download the PDF from.
        dest: Local path to save the downloaded file.

    Raises:
        httpx.HTTPError: If the download fails or returns non-200.
    """
    import httpx

    dest.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)

    logger.info(f"Downloaded {len(response.content)} bytes to {dest}")


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

    linkedin_dir = get_data_path("linkedin")

    if not linkedin_dir.exists():
        raise FileNotFoundError(
            f"LinkedIn data directory not found at {linkedin_dir}.\n"
            "Export your LinkedIn data and place CSVs in data/linkedin/.\n"
            "LinkedIn → Settings & Privacy → Data Privacy → "
            "Get a copy of your data → Request archive."
        )

    logger.info(f"Starting LinkedIn ingestion from: {linkedin_dir}")

    await _clear_source(["linkedin"], db)

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

    await _clear_source(["sanity", "testimonial"], db)

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


async def ingest_resume(db: AsyncSession) -> int:
    """Ingest resume PDF into the knowledge base.

    Uses section-aware chunking for resumes — splits on known
    section headers rather than word count. This ensures each
    chunk answers a distinct type of question.

    Clears all existing resume chunks before re-ingesting.
    Idempotent — safe to run multiple times without duplicates.

    Args:
        db: Active async database session.

    Returns:
        Number of chunks stored. 0 if PDF produced no content.

    Raises:
        FileNotFoundError: If data/resume.pdf does not exist.
        pypdf.errors.PdfReadError: If file is not a valid PDF.
    """

    await _clear_source(["resume"], db)

    if settings.DEV_MODE:
        logger.info("DEV_MODE enabled — using seeded resume content")
        text = SEED_RESUME_TEXT
    else:
        local_path = get_data_path("resume.pdf")

        if not local_path.exists():
            raise FileNotFoundError(
                f"Resume PDF not found at {local_path}.\n"
                "Place your resume PDF at data/resume.pdf before running ingestion."
            )

        logger.info(f"Starting resume ingestion from: {local_path}")
        text = await load_pdf_from_data(local_path=local_path)

    # Use section-aware chunking for resumes — better retrieval precision
    chunks = _chunk_resume_by_section(text)

    if not chunks:
        logger.warning("No chunks produced from resume PDF — check file content")
        return 0

    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    await _store_chunks(chunks, embeddings, db)
    logger.success(f"Resume ingestion complete — {len(chunks)} chunks stored")
    return len(chunks)


def _chunk_resume_by_section(text: str) -> list[dict]:
    """Split resume text into chunks by section header.

    Produces one chunk per section so each chunk answers a
    distinct type of question — experience vs skills vs education.
    Falls back to word-count chunking if no sections are detected.

    Section headers detected:
        Summary, Professional Experience, Employment History,
        Education, Technical Skills

    Args:
        text: Full extracted text from resume PDF.

    Returns:
        List of chunk dicts with content, source, source_id,
        chunk_index keys.
    """
    # Known section headers in order of appearance
    section_headers = [
        "Summary",
        "Professional Experience",
        "Professional  Experience",  # double space fallback
        "Employment History",
        "Education",
        "Technical Skills",
    ]

    # Split text into sections by finding header positions
    sections = []
    remaining = text

    for _, header in enumerate(section_headers):
        if header in remaining:
            # Split at this header
            parts = remaining.split(header, 1)
            pre = parts[0].strip()

            # Pre-header text is the previous section's content
            if pre and sections:
                sections[-1]["content"] += f"\n{pre}"
            elif pre:
                # Content before first header — add as intro chunk
                sections.append(
                    {
                        "content": pre,
                        "header": "Introduction",
                    }
                )

            sections.append(
                {
                    "content": header,
                    "header": header,
                }
            )
            remaining = parts[1] if len(parts) > 1 else ""

    # Remaining text belongs to the last section
    if remaining.strip() and sections:
        sections[-1]["content"] += f"\n{remaining.strip()}"

    if not sections:
        # No sections detected — fall back to word-count chunking
        logger.warning(
            "No resume sections detected — falling back to word-count chunking"
        )
        return chunk_document(text, source="resume", source_id="resume.pdf")

    return [
        {
            "content": section["content"].strip(),
            "source": "resume",
            "source_id": f"resume-{section['header'].lower().replace(' ', '-')}",
            "chunk_index": i,
        }
        for i, section in enumerate(sections)
        if section["content"].strip()
    ]
