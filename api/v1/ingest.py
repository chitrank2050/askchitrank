"""
Ingest webhook endpoint.

Called by Sanity CMS when content changes. Triggers re-ingestion
of Sanity documents and invalidates the response cache so users
get fresh answers after portfolio updates.

Endpoints:
    POST /v1/ingest

Sanity webhook setup:
    Sanity dashboard → API → Webhooks → Create webhook
    URL: https://your-deployment.up.railway.app/v1/ingest
    Trigger: on publish, on delete
    Secret: set INGEST_WEBHOOK_SECRET in config and Sanity dashboard
"""

import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.rate_limit import limiter
from src.core.config import settings
from src.core.logger import logger
from src.db.connection import get_db
from src.ingestion.pipeline import ingest_sanity
from src.retrieval.cache import invalidate_cache

router = APIRouter()


def _verify_webhook_signature(
    payload: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Verify Sanity webhook signature.

    Sanity signs webhooks with format: t=<timestamp>,v1=<hmac>
    Signature is HMAC-SHA256 of "<timestamp>.<body>" using the secret.

    Args:
        payload: Raw request body bytes.
        signature_header: Value of x-sanity-webhook-signature header.
        secret: Webhook secret from config.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature_header:
        return False

    try:
        # Parse "t=1234567890,v1=abc123..."
        parts = dict(part.split("=", 1) for part in signature_header.split(","))
        timestamp = parts.get("t", "")
        signature = parts.get("v1", "")

        if not timestamp or not signature:
            return False

        # Sanity signs: "<timestamp>.<body>"
        signed_content = f"{timestamp}.".encode() + payload

        expected = hmac.new(
            secret.encode("utf-8"),
            signed_content,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    except Exception:
        return False


@router.post(
    "/ingest",
    summary="Sanity CMS webhook — re-ingest on content change",
    description=(
        "Called by Sanity when portfolio content changes. "
        "Re-ingests all Sanity documents and invalidates the response cache."
    ),
)
@limiter.limit("10/minute")
async def ingest_webhook(
    request: Request,
    x_sanity_webhook_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Sanity CMS webhook — re-ingest and invalidate cache.

    Verifies the webhook signature if INGEST_WEBHOOK_SECRET is configured,
    then re-ingests Sanity documents and clears the response cache.

    Args:
        request: FastAPI request — used to read raw body for signature verification.
        x_sanity_webhook_signature: HMAC signature from Sanity.
        db: Database session injected by FastAPI dependency.

    Returns:
        Dict with chunks_ingested and cache_invalidated counts.

    Raises:
        HTTPException 401: If webhook signature verification fails.
        HTTPException 500: If ingestion fails.
    """
    # Verify webhook signature if secret is configured
    if settings.INGEST_WEBHOOK_SECRET:
        payload = await request.body()
        if not _verify_webhook_signature(
            payload,
            x_sanity_webhook_signature,
            settings.INGEST_WEBHOOK_SECRET,
        ):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    logger.info("Sanity webhook received — re-ingesting content")

    try:
        # Invalidate cache first — old answers are stale immediately
        invalidated = await invalidate_cache(db)
        logger.info(f"Invalidated {invalidated} cache entries")

        # Re-ingest Sanity documents
        chunks = await ingest_sanity(db)
        logger.success(f"Webhook ingestion complete — {chunks} chunks stored")

        return {
            "status": "ok",
            "chunks_ingested": chunks,
            "cache_invalidated": invalidated,
        }

    except Exception as e:
        logger.error(f"Webhook ingestion failed: {e}", exc_info=True)
        # generic message for security, don't leak internals
        raise HTTPException(
            status_code=500,
            detail="Ingestion process failed on the server. Our team has been notified.",
        ) from e
