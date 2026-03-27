"""
Text chunking for the ingestion pipeline.

Splits long documents into overlapping chunks so each chunk fits
within the embedding model's context window and contains enough
context to be meaningful in isolation.

Responsibility: split text into chunks. Nothing else.
Does NOT: embed, store, or load documents.

Typical usage:
    from src.ingestion.chunker import chunk_document, chunk_loaded_document

    chunks = chunk_document(text, source="resume", source_id="resume.pdf")
"""

import re
from collections.abc import Mapping

from src.core.config import settings
from src.core.logger import logger


def _word_count(text: str) -> int:
    return len(text.split())


def _clean_block(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines).strip()


def _pack_units(units: list[str], max_words: int, joiner: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for unit in units:
        unit_words = _word_count(unit)
        if current and current_words + unit_words > max_words:
            chunks.append(joiner.join(current).strip())
            current = [unit]
            current_words = unit_words
            continue

        current.append(unit)
        current_words += unit_words

    if current:
        chunks.append(joiner.join(current).strip())

    return chunks


def _split_large_block(block: str, max_words: int) -> list[str]:
    cleaned = _clean_block(block)
    if not cleaned:
        return []

    if _word_count(cleaned) <= max_words:
        return [cleaned]

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if len(lines) > 1:
        packed_lines: list[str] = []
        for line in lines:
            packed_lines.extend(_split_large_block(line, max_words))
        return _pack_units(packed_lines, max_words, "\n")

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", cleaned)
        if sentence.strip()
    ]
    if len(sentences) > 1:
        packed_sentences: list[str] = []
        for sentence in sentences:
            packed_sentences.extend(_split_large_block(sentence, max_words))
        return _pack_units(packed_sentences, max_words, " ")

    words = cleaned.split()
    return [
        " ".join(words[index : index + max_words]).strip()
        for index in range(0, len(words), max_words)
    ]


def _split_into_blocks(text: str, max_words: int) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    ]
    if not paragraphs:
        return []

    blocks: list[str] = []
    for paragraph in paragraphs:
        blocks.extend(_split_large_block(paragraph, max_words))

    return blocks


def _overlap_tail(blocks: list[str], target_words: int) -> list[str]:
    if not blocks or target_words <= 0:
        return []

    overlap: list[str] = []
    overlap_words = 0
    for block in reversed(blocks):
        overlap.insert(0, block)
        overlap_words += _word_count(block)
        if overlap_words >= target_words:
            break

    return overlap


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks while preserving block boundaries.

    Paragraphs and line-level blocks are kept together when possible
    so semantic units like fields, bullets, and short sections are not
    arbitrarily cut apart. Falls back to sentence and word splitting
    when a single block is still too large.

    Args:
        text: Raw text to split into chunks.
        chunk_size: Target words per chunk. Defaults to settings.CHUNK_SIZE.
        chunk_overlap: Words of overlap between chunks.
            Defaults to settings.CHUNK_OVERLAP.

    Returns:
        List of text chunks. Empty list if text is empty.

    Example:
        >>> chunks = chunk_text("long document text...", chunk_size=500)
        >>> len(chunks)
        3
    """
    chunk_size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
    chunk_overlap = settings.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap

    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        return []

    chunk_overlap = max(0, min(chunk_overlap, max(chunk_size - 1, 0)))
    blocks = _split_into_blocks(text, chunk_size)
    if not blocks:
        return []

    chunks: list[str] = []
    current_blocks: list[str] = []
    current_words = 0

    for block in blocks:
        block_words = _word_count(block)

        if current_blocks and current_words + block_words > chunk_size:
            chunks.append("\n\n".join(current_blocks).strip())
            current_blocks = _overlap_tail(current_blocks, chunk_overlap)
            current_words = sum(_word_count(item) for item in current_blocks)

            while current_blocks and current_words + block_words > chunk_size:
                current_words -= _word_count(current_blocks[0])
                current_blocks = current_blocks[1:]

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chunks.append("\n\n".join(current_blocks).strip())

    logger.debug(f"Chunked text into {len(chunks)} chunks")
    return chunks


def chunk_document(
    text: str,
    source: str,
    source_id: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    chunk_prefix: str | None = None,
) -> list[dict]:
    """Split a document into chunks with source metadata.

    Wraps chunk_text with source metadata so each chunk can be stored
    and traced back to its origin document. When chunk_prefix is
    provided, it is repeated on every chunk produced from the document
    so later chunks do not lose important context like project title,
    evidence type, or section label.

    Args:
        text: Raw document text to chunk.
        source: Document origin — 'resume' or 'sanity'.
        source_id: Filename or Sanity document ID for traceability.
        chunk_size: Target words per chunk.
        chunk_overlap: Words of overlap between consecutive chunks.
        chunk_prefix: Stable prefix repeated on each emitted chunk.

    Returns:
        List of dicts with keys: content, source, source_id, chunk_index.

    Example:
        >>> chunks = chunk_document(text, "sanity", "project-abc123")
        >>> chunks[0].keys()
        dict_keys(['content', 'source', 'source_id', 'chunk_index'])
    """
    normalized_text = text.strip()
    normalized_prefix = chunk_prefix.strip() if chunk_prefix else ""

    if not normalized_text:
        return []

    if not normalized_prefix:
        chunks = chunk_text(normalized_text, chunk_size, chunk_overlap)
    else:
        chunk_size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
        chunk_overlap = (
            settings.CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap
        )

        prefix_words = _word_count(normalized_prefix)
        if prefix_words >= chunk_size:
            logger.warning(
                "Chunk prefix is too large for configured chunk size; "
                "falling back to unprefixed chunking"
            )
            chunks = chunk_text(normalized_text, chunk_size, chunk_overlap)
        else:
            body_text = normalized_text
            if body_text.startswith(normalized_prefix):
                body_text = body_text.removeprefix(normalized_prefix).strip()

            effective_size = max(chunk_size - prefix_words, 1)
            effective_overlap = min(chunk_overlap, max(effective_size - 1, 0))

            if not body_text:
                chunks = [normalized_text]
            else:
                body_chunks = chunk_text(body_text, effective_size, effective_overlap)
                if len(body_chunks) <= 1:
                    chunks = [normalized_text]
                else:
                    chunks = [
                        f"{normalized_prefix}\n\n{body_chunk}".strip()
                        for body_chunk in body_chunks
                    ]

    return [
        {
            "content": chunk,
            "source": source,
            "source_id": source_id,
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]


def chunk_loaded_document(
    document: Mapping[str, str],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """Chunk a loader-produced document dict with optional repeated context."""
    return chunk_document(
        text=document["text"],
        source=document["source"],
        source_id=document["source_id"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_prefix=document.get("chunk_prefix"),
    )
