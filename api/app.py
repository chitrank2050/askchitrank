"""
FastAPI application factory.

Creates and configures the FastAPI application — registers routes,
middleware, lifespan, and exception handlers.

Responsibility: assemble the application. Nothing else.
Does NOT: define routes, handle requests, or run business logic.

Usage:
    make api
    uv run python -m src.api.app
"""

import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.utils.middleware import add_request_id
from api.utils.rate_limit import limiter
from api.v1 import router as v1_router
from src.core import bootstrap
from src.core.api_lifespan import api_lifespan
from src.core.config import settings
from src.core.logger import logger


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers middleware, routes, lifespan, and exception handlers.
    Called once at startup — never call this inside a request handler.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        openapi_url=settings.API_OPENAPI_URL,
        lifespan=api_lifespan,
    )

    app.middleware("http")(add_request_id)

    # ── Rate limiting ──────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
    app.add_middleware(
        SlowAPIMiddleware  # ty:ignore[invalid-argument-type]
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    # Allow portfolio frontend to call the API from the browser
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        # Restrict in production — expand only for known frontend origins
        allow_origins=settings.API_ALLOWED_ORIGINS,
        allow_credentials=settings.API_ALLOW_CREDENTIALS,
        allow_methods=settings.API_ALLOWED_METHODS,
        allow_headers=settings.API_ALLOWED_HEADERS,
    )

    # ── Routes ─────────────────────────────────────────────────────────────
    # Mount v1 — all endpoints live under /v1
    app.include_router(v1_router, prefix=settings.API_PREFIX)

    return app


# Application singleton — import this in tests and other modules
app = create_app()


def main() -> None:
    """Start the Uvicorn server.

    Reads host, port, and reload settings from config.
    Called by 'make api' via src.main.
    """
    uvicorn.run(
        "src.api.app:app",
        host=settings.API_HOST,
        port=int(settings.API_PORT),
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    try:
        bootstrap()
        main()
    except KeyboardInterrupt:
        logger.warning("🛑 Application interrupted by user.")
        sys.exit(0)
