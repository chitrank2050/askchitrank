"""api/app.py

FastAPI application factory.

Creates and configures the FastAPI application — registers routes,
middleware, lifespan, and exception handlers.

All errors return standardized JSON via the APIError exception system.
Stack traces are never exposed to clients in any environment.

Responsibility: assemble the application. Nothing else.
Does NOT: define routes, handle requests, or run business logic.

Usage:
    make api
    uv run python -m src.main api
"""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.utils.errors import APIError, api_error_handler
from api.utils.middleware import add_request_id, add_security_headers
from api.utils.rate_limit import limiter
from api.v1 import router as v1_router
from src.core import bootstrap
from src.core.api_lifespan import api_lifespan
from src.core.config import settings
from src.core.logger import logger


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers middleware, routes, lifespan, and exception handlers.
    Called once at startup — never call inside a request handler.

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

    # ── Exception handlers ────────────────────────────────────────────────
    # All exceptions funnel through typed APIError responses.
    # Stack traces never reach the client in any environment.

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        """Handle all typed APIError exceptions.

        These are raised deliberately throughout the application
        with specific error codes and user-friendly messages.
        """
        return api_error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic/FastAPI request validation failures.

        Converts FastAPI's default validation error format to our
        standardized APIError shape. Details only shown in debug mode.
        """
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")

        # Build a readable summary of what failed
        error_details = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )

        error = APIError.validation_error(
            error_details if settings.API_DEBUG else "Check your request body."
        )
        return api_error_handler(request, error)

    @app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        """Handle slowapi rate limit exceeded errors."""
        logger.warning(
            f"Rate limit exceeded — IP: {request.client.host if request.client else 'unknown'}"
        )
        error = APIError.rate_limited()
        return api_error_handler(request, error)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for any unhandled exceptions.

        Logs full traceback internally. Client always receives a generic
        500 message — stack traces never leak to the caller.
        """
        logger.critical(
            f"Unhandled exception on {request.url.path}: {exc}",
            exc_info=True,
        )
        error = APIError.internal()
        return api_error_handler(request, error)

    # ── Middleware ─────────────────────────────────────────────────────────
    # Execution order is LIFO — last registered runs first on request.
    # CORS → SlowAPI → Security headers → Request ID

    app.middleware("http")(add_request_id)
    app.middleware("http")(add_security_headers)

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
    app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.API_ALLOWED_ORIGINS,
        allow_credentials=settings.API_ALLOW_CREDENTIALS,
        allow_methods=settings.API_ALLOWED_METHODS,
        allow_headers=settings.API_ALLOWED_HEADERS,
    )

    # ── Routes ─────────────────────────────────────────────────────────────
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
        "api.app:app",
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
        logger.warning("Application interrupted by user.")
        sys.exit(0)
