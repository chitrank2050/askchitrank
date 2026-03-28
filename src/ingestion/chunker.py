"""
Text chunking for the ingestion pipeline.

Splits long documents into retrieval-friendly chunks while preserving
structure and grouping adjacent related blocks when possible.

The chunker is intentionally hybrid:
- keep paragraph and line-group boundaries where possible
- semantically merge nearby related blocks
- split early when labeled blocks clearly change topic
- fall back to sentence or word slicing only for oversized blocks
- repeat stable prefixes later via chunk_document() when needed

Responsibility: split text into chunks. Nothing else.
Does NOT: embed, store, or load documents.

Typical usage:
    from src.ingestion.chunker import chunk_document, chunk_loaded_document

    chunks = chunk_document(text, source="resume", source_id="resume.pdf")
"""

import re
from collections.abc import Mapping
from functools import lru_cache

from src.core.config import settings
from src.core.logger import logger
from src.dev.local_embeddings import embed_text

_SEMANTIC_GROUP_DIMENSIONS = 128
_SEMANTIC_MERGE_THRESHOLD = 0.16
_SEMANTIC_SPLIT_THRESHOLD = 0.08
_MIN_CHUNK_FILL_RATIO_FOR_EARLY_SPLIT = 0.35
_MIN_WORDS_FOR_EARLY_SPLIT = 8


def _word_count(text: str) -> int:
    """Return a simple whitespace word count."""
    return len(text.split())


def _clean_block(text: str) -> str:
    """Normalize whitespace inside a candidate block while keeping lines."""
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines).strip()


@lru_cache(maxsize=2048)
def _block_embedding(text: str) -> tuple[float, ...]:
    """Cache local embeddings used only for intra-document grouping."""
    return tuple(embed_text(text, _SEMANTIC_GROUP_DIMENSIONS))


def _semantic_similarity(left: str, right: str) -> float:
    """Return cosine-like similarity for two blocks using local embeddings."""
    if not left.strip() or not right.strip():
        return 0.0

    left_embedding = _block_embedding(left.strip())
    right_embedding = _block_embedding(right.strip())
    return sum(x * y for x, y in zip(left_embedding, right_embedding, strict=False))


def _block_prefix(block: str) -> str | None:
    """Extract a lightweight structural label from a block when present."""
    for line in block.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        if cleaned.startswith("- "):
            return "bullet"

        match = re.match(r"([A-Za-z][A-Za-z /&+-]{1,40}):", cleaned)
        if match:
            return match.group(1).strip().lower()

        if len(cleaned.split()) <= 6 and cleaned == cleaned.title():
            return cleaned.lower()

        return None

    return None


def _same_block_family(left: str, right: str) -> bool:
    """Check whether two blocks appear to belong to the same labeled family."""
    left_prefix = _block_prefix(left)
    right_prefix = _block_prefix(right)

    if not left_prefix or not right_prefix:
        return False

    return left_prefix == right_prefix


def _pack_units(units: list[str], max_words: int, joiner: str) -> list[str]:
    """Pack already-split units into chunks without exceeding the word budget."""
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
    """Split an oversized block recursively by lines, then sentences, then words."""
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
    """Turn raw text into normalized paragraph-sized blocks."""
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


def _group_blocks_semantically(blocks: list[str], max_words: int) -> list[str]:
    """Merge adjacent related blocks when doing so stays within chunk size."""
    if len(blocks) <= 1:
        return blocks

    groups: list[str] = []
    current_group: list[str] = [blocks[0]]
    current_words = _word_count(blocks[0])

    for block in blocks[1:]:
        block_words = _word_count(block)
        current_text = "\n\n".join(current_group).strip()
        similarity = _semantic_similarity(current_text, block)
        should_merge = current_words + block_words <= max_words and (
            _same_block_family(current_group[-1], block)
            or similarity >= _SEMANTIC_MERGE_THRESHOLD
            or (
                current_words < max(_MIN_WORDS_FOR_EARLY_SPLIT, max_words // 4)
                and similarity >= _SEMANTIC_SPLIT_THRESHOLD
            )
        )

        if should_merge:
            current_group.append(block)
            current_words += block_words
            continue

        groups.append(current_text)
        current_group = [block]
        current_words = block_words

    if current_group:
        groups.append("\n\n".join(current_group).strip())

    return groups


def _overlap_tail(blocks: list[str], target_words: int) -> list[str]:
    """Return the trailing blocks needed to satisfy overlap for size splits."""
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


def _should_split_for_semantics(
    current_blocks: list[str],
    next_block: str,
    chunk_size: int,
) -> bool:
    """Decide whether a topic change warrants splitting before size requires it."""
    if not current_blocks:
        return False

    current_text = "\n\n".join(current_blocks).strip()
    current_words = _word_count(current_text)
    current_prefix = _block_prefix(current_blocks[-1])
    next_prefix = _block_prefix(next_block)

    if (
        current_prefix
        and next_prefix
        and current_prefix != next_prefix
        and _semantic_similarity(current_text, next_block) < _SEMANTIC_SPLIT_THRESHOLD
    ):
        return True

    min_words_for_split = max(
        _MIN_WORDS_FOR_EARLY_SPLIT,
        int(chunk_size * _MIN_CHUNK_FILL_RATIO_FOR_EARLY_SPLIT),
    )

    if current_words < min_words_for_split:
        return False

    if _same_block_family(current_blocks[-1], next_block):
        return False

    return _semantic_similarity(current_text, next_block) < _SEMANTIC_SPLIT_THRESHOLD


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """Split text into chunks while preserving block boundaries.

    Paragraphs and line-level blocks are kept together when possible
    so semantic units like fields, bullets, and short sections are not
    arbitrarily cut apart. Adjacent related blocks are grouped using
    lightweight local semantic similarity before final chunk packing.
    Falls back to sentence and word splitting only when a single block
    is still too large.

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
    blocks = _group_blocks_semantically(blocks, chunk_size)

    chunks: list[str] = []
    current_blocks: list[str] = []
    current_words = 0

    for block in blocks:
        block_words = _word_count(block)

        should_split_by_size = (
            current_blocks and current_words + block_words > chunk_size
        )
        should_split_by_semantics = (
            current_blocks
            and not should_split_by_size
            and _should_split_for_semantics(current_blocks, block, chunk_size)
        )

        if should_split_by_size or should_split_by_semantics:
            chunks.append("\n\n".join(current_blocks).strip())
            if should_split_by_size:
                current_blocks = _overlap_tail(current_blocks, chunk_overlap)
                current_words = sum(_word_count(item) for item in current_blocks)

                while current_blocks and current_words + block_words > chunk_size:
                    current_words -= _word_count(current_blocks[0])
                    current_blocks = current_blocks[1:]
            else:
                current_blocks = []
                current_words = 0

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chunks.append("\n\n".join(current_blocks).strip())

    logger.debug(
        "Chunked text into {} chunks from {} semantic groups",
        len(chunks),
        len(blocks),
    )
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
    """Chunk a loader-produced document dict with optional repeated context.

    Expected document keys:
        text: Body text to chunk.
        source: Source label stored in the database.
        source_id: Stable source identifier for traceability.
        chunk_prefix: Optional prefix repeated on every emitted chunk.
    """
    return chunk_document(
        text=document["text"],
        source=document["source"],
        source_id=document["source_id"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_prefix=document.get("chunk_prefix"),
    )
