"""
SQLAlchemy ORM models.

Defines three tables:
    knowledge_chunks  — embedded document chunks from resume and Sanity CMS
    response_cache    — cached question→response pairs to reduce LLM API cost
    conversations     — conversation history per browser session

Responsibility: define table schemas. Nothing else.
Does NOT: run queries, handle business logic, or manage connections.

Typical usage:
    from src.db.models import KnowledgeChunk, ResponseCache, Conversation
"""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.config import settings
from src.db.connection import Base


class KnowledgeChunk(Base):
    """Stores embedded document chunks from resume and Sanity CMS.

    Each chunk is a short passage of text (~500 tokens) paired with
    its vector embedding. Similarity search over embeddings finds the
    most relevant chunks for a given question.

    Attributes:
        id: UUID primary key.
        source: Origin of the chunk — 'resume' or 'sanity'.
        source_id: Filename or Sanity document ID for traceability.
        content: Raw text of the chunk shown to the LLM as context.
        embedding: Vector representation for similarity search.
        chunk_index: Position of this chunk within its source document.
        created_at: UTC timestamp of ingestion.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS))
    chunk_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ResponseCache(Base):
    """Caches question→response pairs to reduce LLM API costs.

    When a new question is semantically similar to a cached question
    (cosine similarity above threshold), the cached response is returned
    immediately without calling the LLM API.

    Cache entries are invalidated via Sanity webhook when source
    content changes — ensuring stale answers are never served.

    Attributes:
        id: UUID primary key.
        question: Original question text from the user.
        question_embedding: Vector embedding of the question for similarity search.
        response: Full LLM response text to return on cache hit.
        source_chunk_ids: JSON array of KnowledgeChunk IDs used to generate response.
        hit_count: Number of times this cached response has been served.
        created_at: UTC timestamp of cache entry creation.
        invalidated_at: UTC timestamp of invalidation. Null means entry is valid.
    """

    __tablename__ = "response_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    question: Mapped[str] = mapped_column(Text)
    question_embedding: Mapped[list] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS)
    )
    response: Mapped[str] = mapped_column(Text)
    source_chunk_ids: Mapped[str] = mapped_column(Text)  # JSON array of UUIDs
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Conversation(Base):
    """Stores conversation history per browser session.

    Enables multi-turn conversations where the chatbot remembers
    context from earlier in the same session. Each message is stored
    as a separate row with a role indicator.

    Attributes:
        id: UUID primary key.
        session_id: Browser session ID or anonymous user identifier.
        role: Message author — 'user' or 'assistant'.
        content: Message text.
        created_at: UTC timestamp of message — used to reconstruct order.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
