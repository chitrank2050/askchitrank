"""api/v1/ingest.py

Ingest webhook endpoint.

Protected by API_TOKEN passed as a query parameter in the webhook URL.
Configure Sanity webhook URL as:
    https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN

This way the same API_TOKEN protects all endpoints consistently.

Endpoints:
    POST /v1/ingest
"""

import hmac

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.errors import APIError
from api.utils.rate_limit import limiter
from src.core.config import settings
from src.core.logger import logger
from src.db.connection import get_db
from src.ingestion.pipeline import ingest_sanity
from src.retrieval.cache import invalidate_cache

router = APIRouter()


@router.post(
    "/ingest",
    summary="Sanity CMS webhook — re-ingest on content change",
    description=(
        "Called by Sanity when portfolio content changes. "
        "Protected by API_TOKEN passed as query parameter. "
        "Configure Sanity webhook URL as: /v1/ingest?token=YOUR_API_TOKEN"
    ),
)
@limiter.limit("10/minute")
async def ingest_webhook(
    request: Request,
    token: str | None = Query(default=None, description="API token for authentication"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Sanity CMS webhook — re-ingest and invalidate cache.

    Verifies the token query parameter against API_TOKEN config.
    Use the same token as the Bearer token for other endpoints.

    Sanity webhook URL format:
        https://your-api.railway.app/v1/ingest?token=YOUR_API_TOKEN

    Args:
        request: FastAPI request.
        token: API token from query parameter.
        db: Database session injected by FastAPI dependency.

    Returns:
        Dict with chunks_ingested counts.

    Raises:
        APIError.missing_token: If token query param is absent.
        APIError.invalid_token: If token does not match API_TOKEN.
        APIError.ingestion_failed: If re-ingestion fails.
    """
    # Verify token — same API_TOKEN used everywhere
    if not settings.API_TOKEN:
        logger.error("API_TOKEN is not configured — refusing webhook")
        raise APIError.internal()

    if not token:
        raise APIError.missing_token()

    if not hmac.compare_digest(token, settings.API_TOKEN):
        raise APIError.invalid_token()

    logger.info("Sanity webhook received — re-ingesting content")

    try:
        # Invalidate cache first — old answers are stale immediately
        invalidated = await invalidate_cache(db)
        logger.info(f"Invalidated {invalidated} cache entries")

        # Re-ingest all Sanity documents
        chunks = await ingest_sanity(db)
        logger.success(f"Webhook ingestion complete — {chunks} chunks stored")

        return {
            "status": "ok",
            "chunks_ingested": chunks,
        }

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Webhook ingestion failed: {e}", exc_info=True)
        raise APIError.ingestion_failed() from e
