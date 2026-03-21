"""
Version 1 API router.

Aggregates all v1 endpoint routers into a single router that app.py
mounts under the /v1 prefix. Adding a new endpoint module means
importing its router here and including it — nothing else changes.

Routers:
    health  — GET /v1/health
    chat    — POST /v1/chat (SSE streaming)
    chat    — GET /v1/chat/safety-metrics
    ingest  — POST /v1/ingest (Sanity webhook)
"""

from fastapi import APIRouter

from . import chat, health, ingest

router = APIRouter()
router.include_router(health.router, tags=["Health"])
router.include_router(chat.router, tags=["Chat"])
router.include_router(ingest.router, tags=["Ingestion"])
