"""
Standardized error response library.

Defines all API error types as typed exceptions and maps them to
consistent HTTP responses. Every error the API can return is defined
here — no scattered HTTPException calls in route handlers.

Usage pattern:
    raise APIError.unauthorized()
    raise APIError.missing_token()
    raise APIError.rate_limited()
    raise APIError.not_found("session")

All errors return JSON in this shape:
    {
        "error": {
            "code": 401,
            "type": "UNAUTHORIZED",
            "message": "...",
            "request_id": "abc12345"
        }
    }

Responsibility: define and raise typed API errors. Nothing else.
Does NOT: handle requests, define routes, or manage auth logic.
"""

from dataclasses import dataclass
from enum import StrEnum

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    """Enumeration of all possible API error types.

    String values are returned in the error response body
    so clients can programmatically handle specific errors.
    """

    # Auth errors
    MISSING_TOKEN = "MISSING_TOKEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"

    # Pipeline errors
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    LLM_FAILED = "LLM_FAILED"
    INGESTION_FAILED = "INGESTION_FAILED"
    CACHE_ERROR = "CACHE_ERROR"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class APIError(Exception):
    """Typed API error that maps directly to an HTTP response.

    Raise this anywhere in the application. The global exception
    handler in app.py converts it to a consistent JSON response.

    Attributes:
        status_code: HTTP status code.
        error_code: Machine-readable error type from ErrorCode enum.
        message: Human-readable error message shown to the client.

    Example:
        raise APIError(
            status_code=401,
            error_code=ErrorCode.MISSING_TOKEN,
            message="API token is required. Include it as: Authorization: Bearer <token>",
        )
    """

    status_code: int
    error_code: ErrorCode
    message: str

    def to_response(self, request_id: str | None = None) -> JSONResponse:
        """Serialize to a FastAPI JSONResponse.

        Args:
            request_id: Request ID from middleware for tracing.

        Returns:
            JSONResponse with standardized error body.
        """
        content: dict = {
            "error": {
                "code": self.status_code,
                "type": self.error_code.value,
                "message": self.message,
            }
        }

        if request_id:
            content["error"]["request_id"] = request_id

        return JSONResponse(status_code=self.status_code, content=content)

    # ── Auth errors ───────────────────────────────────────────────────────

    @classmethod
    def missing_token(cls) -> "APIError":
        """No Authorization header provided."""
        return cls(
            status_code=401,
            error_code=ErrorCode.MISSING_TOKEN,
            message=(
                "API token is required. "
                "Include it as: Authorization: Bearer <your-token>"
            ),
        )

    @classmethod
    def invalid_token(cls) -> "APIError":
        """Authorization header present but token is wrong."""
        return cls(
            status_code=401,
            error_code=ErrorCode.INVALID_TOKEN,
            message="Invalid API token. Check your token and try again.",
        )

    @classmethod
    def unauthorized(cls) -> "APIError":
        """Generic authorization failure."""
        return cls(
            status_code=403,
            error_code=ErrorCode.UNAUTHORIZED,
            message="You are not authorized to perform this action.",
        )

    # ── Rate limiting ─────────────────────────────────────────────────────

    @classmethod
    def rate_limited(cls, limit: str = "30/minute") -> "APIError":
        """Client has exceeded the rate limit."""
        return cls(
            status_code=429,
            error_code=ErrorCode.RATE_LIMITED,
            message=(
                f"Rate limit exceeded ({limit}). "
                "Please slow down and try again in a moment."
            ),
        )

    # ── Validation errors ─────────────────────────────────────────────────

    @classmethod
    def validation_error(cls, details: str) -> "APIError":
        """Request body failed schema validation."""
        return cls(
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Request validation failed: {details}",
        )

    @classmethod
    def invalid_input(cls, field: str, reason: str) -> "APIError":
        """A specific field has an invalid value."""
        return cls(
            status_code=400,
            error_code=ErrorCode.INVALID_INPUT,
            message=f"Invalid value for '{field}': {reason}",
        )

    # ── Pipeline errors ───────────────────────────────────────────────────

    @classmethod
    def embedding_failed(cls) -> "APIError":
        """Voyage AI embedding call failed."""
        return cls(
            status_code=503,
            error_code=ErrorCode.EMBEDDING_FAILED,
            message=(
                "Failed to process your question. "
                "The embedding service may be temporarily unavailable. "
                "Please try again in a moment."
            ),
        )

    @classmethod
    def llm_failed(cls) -> "APIError":
        """Groq LLM call failed."""
        return cls(
            status_code=503,
            error_code=ErrorCode.LLM_FAILED,
            message=(
                "Failed to generate a response. "
                "The language model service may be temporarily unavailable. "
                "Please try again in a moment."
            ),
        )

    @classmethod
    def ingestion_failed(cls) -> "APIError":
        """Ingestion pipeline failed."""
        return cls(
            status_code=500,
            error_code=ErrorCode.INGESTION_FAILED,
            message="Content ingestion failed. Check server logs for details.",
        )

    # ── Server errors ─────────────────────────────────────────────────────

    @classmethod
    def internal(cls) -> "APIError":
        """Catch-all for unexpected server errors."""
        return cls(
            status_code=500,
            error_code=ErrorCode.INTERNAL_ERROR,
            message=(
                "An unexpected error occurred. "
                "Please try again. If the problem persists, "
                "contact chitrank2050@gmail.com"
            ),
        )

    @classmethod
    def service_unavailable(cls, service: str) -> "APIError":
        """An external service is unavailable."""
        return cls(
            status_code=503,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message=(
                f"The {service} service is temporarily unavailable. "
                "Please try again in a moment."
            ),
        )


def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """FastAPI exception handler for APIError.

    Registered in app.py via:
        app.add_exception_handler(APIError, api_error_handler)

    Args:
        request: FastAPI request — used to extract request ID.
        exc: The raised APIError instance.

    Returns:
        Standardized JSON error response.
    """
    request_id = getattr(request.state, "request_id", None)
    return exc.to_response(request_id=request_id)
