"""
Database package.

Provides SQLAlchemy async engine, session management,
and ORM models for knowledge chunks, response cache,
and conversation history.

Typical usage:
    from src.db.connection import get_db
    from src.db.models import KnowledgeChunk, ResponseCache, Conversation
"""

from .connection import AsyncSessionLocal, Base, get_db, init_db
from .models import Conversation, KnowledgeChunk, ResponseCache

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "Conversation",
    "KnowledgeChunk",
    "ResponseCache",
    "get_db",
    "init_db",
]
