"""
FastAPI lifespan context manager for application startup and shutdown.

Responsibility: own the lifecycle of shared resources. Nothing else.
Does NOT: define routes, handle requests, or run inference.

Pattern: FastAPI lifespan (replaces deprecated on_event handlers).
The predictor is stored on app.state so all routes access the same
instance without re-loading the model per request.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .logger import logger


@asynccontextmanager
async def api_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    On shutdown, logs teardown — add cleanup logic here if future
    resources require explicit release (DB connections, thread pools).

    Args:
        app: The FastAPI application instance.

    Yields:
        None — control returns to FastAPI to serve requests.

    Example:
        >>> app = FastAPI(lifespan=lifespan)
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting Ask Chitrank API")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Ask Chitrank API")
