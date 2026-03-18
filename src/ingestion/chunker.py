"""
Text chunking for the ingestion pipeline.

Splits long documents into overlapping chunks so each chunk
fits within the embedding model's context window and contains
enough context to be meaningful in isolation.

Responsibility: split text into chunks. Nothing else.
Does NOT: embed, store, or load documents.

Typical usage:
    from src.ingestion.chunker import chunk_text

    chunks = chunk_text("long document text...")
"""

from src.core.config import settings
from src.core.logger import logger


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks by word count.

    Uses word-boundary splitting with overlap to ensure context
    continuity between chunks. Each chunk is self-contained enough
    to answer questions without requiring adjacent chunks.

    Args:
        text: Raw text to split into chunks.
        chunk_size: Target words per chunk. Defaults to settings.CHUNK_SIZE.
        chunk_overlap: Words of overlap between chunks.
            Defaults to settings.CHUNK_OVERLAP.

    Returns:
        List of text chunks. Empty list if text is empty.

    Example:
        >>> chunks = chunk_text("long document...", chunk_size=500)
        >>> len(chunks)
        3
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        # Move forward by chunk_size minus overlap
        # ensures consecutive chunks share context
        start += chunk_size - chunk_overlap

        if start >= len(words):
            break

    logger.debug(f"Chunked text into {len(chunks)} chunks")
    return chunks


def chunk_document(
    text: str,
    source: str,
    source_id: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """Split a document into chunks with metadata.

    Wraps chunk_text with source metadata so each chunk
    can be stored and traced back to its origin document.

    Args:
        text: Raw document text to chunk.
        source: Document origin — 'resume' or 'sanity'.
        source_id: Filename or Sanity document ID.
        chunk_size: Target words per chunk.
        chunk_overlap: Words of overlap between chunks.

    Returns:
        List of dicts with keys: content, source, source_id, chunk_index.

    Example:
        >>> chunks = chunk_document(text, "sanity", "project-123")
        >>> chunks[0].keys()
        dict_keys(['content', 'source', 'source_id', 'chunk_index'])
    """
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    return [
        {
            "content": chunk,
            "source": source,
            "source_id": source_id,
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]
