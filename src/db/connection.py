"""src/db/connection.py

Database connection and session management.

Provides async SQLAlchemy engine and session factory for FastAPI
dependency injection. Uses asyncpg driver for async PostgreSQL.

Responsibility: manage database connections. Nothing else.
Does NOT: define models, run queries, or handle business logic.

Typical usage:
    from src.db.connection import get_db

    @router.post("/chat")
    async def chat(db: AsyncSession = Depends(get_db)):
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings
from src.core.logger import logger


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All models inherit from this class to share the same
    metadata registry — required for Alembic autogenerate
    and create_all to discover tables automatically.
    """

    pass


# Async engine — used by FastAPI at runtime
# pool_pre_ping=True verifies connections before use,
# handling Supabase free tier pause behaviour gracefully
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # set True to log raw SQL during debugging
    pool_size=5,  # connections kept alive in the pool
    max_overflow=10,  # extra connections allowed above pool_size
    pool_pre_ping=True,
)

# Session factory — produces AsyncSession instances per request
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session as a FastAPI dependency.

    Opens a session, yields it to the route handler, commits
    on success, and rolls back on any exception. Session is
    always closed after the request completes.

    Yields:
        AsyncSession: Active database session for the request.

    Raises:
        Exception: Re-raises any exception after rolling back
            the session to prevent partial writes.

    Example:
        >>> @router.post("/chat")
        >>> async def chat(db: AsyncSession = Depends(get_db)):
        ...     result = await db.execute(select(KnowledgeChunk))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables defined in ORM models at application startup.

    Called once during FastAPI lifespan startup.
    Disposes cached connections first to ensure fresh schema
    detection after migrations.

    Note:
        Does NOT run Alembic migrations — use 'make db-migrate'
        for schema changes. This only creates missing tables.
    """
    async with engine.begin() as conn:
        # Dispose cached connections before schema operations
        # prevents stale connection state after migrations
        await engine.dispose()
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised")
