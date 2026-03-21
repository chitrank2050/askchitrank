"""Deterministic local embeddings for development mode.

These vectors are intentionally simple and cheap. They are not meant to
match provider quality; they only preserve enough semantic structure to
exercise caching, pgvector search, and seeded ingestion locally.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def embed_text(text: str, dimensions: int) -> list[float]:
    """Produce a deterministic, normalized vector for a text string."""
    vector = [0.0] * dimensions
    tokens = _tokenize(text)

    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()

        # Spread one token across a few indices so short texts are less sparse.
        for offset in range(0, 12, 3):
            index = int.from_bytes(digest[offset : offset + 2], "big") % dimensions
            sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
            weight = 1.0 + (digest[offset] / 255.0) * 0.25
            vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector

    return [value / norm for value in vector]


def embed_texts(texts: list[str], dimensions: int) -> list[list[float]]:
    """Vectorize a list of texts with the local deterministic embedder."""
    return [embed_text(text, dimensions) for text in texts]
