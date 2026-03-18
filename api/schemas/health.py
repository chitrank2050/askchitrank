"""
Response schema for the API health check endpoint.

Responsibility: define and validate the shape of GET /v1/health.
Used by load balancers, uptime monitors, and deployment health checks.

Responsibility: define API contracts. Nothing else.
Does NOT: handle requests, call the LLM, or manage sessions.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for GET /v1/health.

    status is 'healthy' when the model is loaded and ready to serve.
    status is 'degraded' when the service is running but the model
    failed to load — requests will return 503 in this state.

    Attributes:
        status: Service status — 'healthy' or 'degraded'.
        version: API version from pyproject.toml.
        timestamp: UTC ISO timestamp of the health check.

    Example:
        >>> response.status
        'healthy'
        >>> response.version
        '1.0.0'
    """

    status: str = Field(..., description="Service status: healthy or degraded")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="UTC ISO timestamp of health check")

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }
