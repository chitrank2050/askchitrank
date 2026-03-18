"""
API token authentication.

Protects all endpoints with Bearer token authentication.
The token is set via the API_TOKEN environment variable.

Usage in route handlers:
    @router.post("/endpoint")
    async def endpoint(
        _: None = Depends(verify_api_token),
    ):
        ...

The dependency raises APIError.missing_token() or APIError.invalid_token()
if the token is absent or wrong — these are caught by the global error
handler in app.py and returned as standardized JSON responses.

Responsibility: verify API tokens. Nothing else.
Does NOT: define routes, manage sessions, or handle business logic.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.utils.errors import APIError
from src.core.config import settings
from src.core.logger import logger

# HTTPBearer extracts the token from the Authorization: Bearer <token> header
# auto_error=False means we handle the missing header ourselves with our
# own error messages instead of FastAPI's generic 403
_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """FastAPI dependency that verifies the API Bearer token.

    Always validates the token — no dev mode bypass.
    API_TOKEN must be set in .env.dev and .env.prod.

    Args:
        credentials: Extracted from Authorization header by HTTPBearer.
            None if the header is absent.

    Raises:
        APIError: MISSING_TOKEN if Authorization header is absent.
        APIError: INVALID_TOKEN if token does not match settings.API_TOKEN.
        APIError: INTERNAL_ERROR if API_TOKEN is not configured.
    """
    if not settings.API_TOKEN:
        logger.error("API_TOKEN is not configured — refusing all requests")
        raise APIError.internal()

    if credentials is None:
        logger.warning("Request missing Authorization header")
        raise APIError.missing_token()

    if credentials.credentials != settings.API_TOKEN:
        logger.warning("Request provided invalid API token")
        raise APIError.invalid_token()

    logger.debug("API token verified successfully")
