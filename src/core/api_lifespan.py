"""
FastAPI lifespan context manager.

Manages initialisation and teardown of shared application resources
at startup and shutdown. Database tables are created at startup.

Responsibility: own the lifecycle of shared resources. Nothing else.
Does NOT: define routes, handle requests, or run business logic.

Pattern: FastAPI lifespan (replaces deprecated on_event handlers).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.logger import logger
from src.db.connection import init_db


@asynccontextmanager
async def api_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    Initialises the database at startup. Add any other startup
    logic here — model loading, connection pool warming, etc.

    Args:
        app: The FastAPI application instance.

    Yields:
        None — control returns to FastAPI to serve requests.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("Starting Ask Chitrank API")

    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database initialisation failed: {e}")
        logger.warning("API starting without database — chat will not function")

    logger.success("Ask Chitrank API ready")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Shutting down Ask Chitrank API")
