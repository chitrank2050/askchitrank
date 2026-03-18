"""
Health check endpoint.

Provides a simple liveness check for the API. Used by Railway
and monitoring tools to verify the service is running.

Health check is intentionally public — no auth required.
Monitoring tools and load balancers must be able to check
health without credentials.

Endpoints:
    GET /v1/health
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from api.schemas.health import HealthResponse
from src.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description=(
        "Returns service health status and version. "
        "Public endpoint — no authentication required."
    ),
)
async def health(request: Request) -> HealthResponse:
    """Return current service health status.

    Intentionally public — no Bearer token required. Monitoring
    tools and Railway health checks must reach this without auth.

    Args:
        request: FastAPI request.

    Returns:
        HealthResponse with status, version, and current UTC timestamp.

    Example:
        GET /v1/health
        → {"status": "healthy", "version": "1.0.0", "timestamp": "..."}
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )
