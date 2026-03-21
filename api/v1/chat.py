"""
Chat endpoint — streams RAG responses via Server-Sent Events.

Accepts a user question and session ID, runs the full RAG pipeline,
and streams the response token by token as SSE events.

All endpoints require a valid Bearer token in the Authorization header.

Endpoints:
    POST /v1/chat
    GET /v1/chat/safety-metrics

SSE event format:
    data: {"type": "token", "content": "..."}                — response token
    data: {"type": "done", "cached": bool, "latency_ms": N}  — stream complete

The chat pipeline now prefers safe fallback answers over error events,
so clients should normally expect only `token` and `done`.
"""

import json as _json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.chat import ChatRequest
from api.schemas.safety_metrics import SafetyMetricsResponse
from api.utils.auth import verify_api_token
from api.utils.errors import APIError
from api.utils.rate_limit import limiter
from src.chat.safety import get_safety_metrics_snapshot
from src.chat.stream import stream_chat_response
from src.core.logger import logger
from src.db.connection import get_optional_db

router = APIRouter()


@router.get(
    "/chat/safety-metrics",
    response_model=SafetyMetricsResponse,
    summary="Inspect chat safety metrics",
    description=(
        "Returns in-process counters for pre-routing, retrieval confidence fallbacks, "
        "and last-resort chat safety responses. Requires a valid Bearer token."
    ),
)
async def safety_metrics(
    _: None = Depends(verify_api_token),
) -> SafetyMetricsResponse:
    """Return current chat safety counters since process start."""
    return SafetyMetricsResponse.model_validate(get_safety_metrics_snapshot())


@router.post(
    "/chat",
    summary="Ask a question about Chitrank",
    description=(
        "Streams a RAG-powered response via Server-Sent Events. "
        "Requires a valid Bearer token in the Authorization header. "
        "Pass the same session_id across requests to maintain conversation context."
    ),
    response_model=None,
)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession | None = Depends(get_optional_db),
    _: None = Depends(verify_api_token),
) -> StreamingResponse | JSONResponse:
    """Stream a RAG response for the user question.

    Runs the chat pipeline: pre-route unsupported questions cheaply,
    otherwise embed → cache check → retrieve → confidence gate →
    prompt → stream LLM → store cache → store conversation.

    Args:
        request: FastAPI request — required by slowapi rate limiter.
        body: Validated ChatRequest with question, session_id, and flags.
        db: Database session injected by FastAPI dependency.
        _: API token verification dependency — raises on invalid token.

    Returns:
        StreamingResponse with SSE content type when stream=True.
        JSONResponse with full response when stream=False.

    Raises:
        APIError.missing_token: If Authorization header is absent.
        APIError.invalid_token: If token does not match API_TOKEN.
        APIError.rate_limited: If 30/minute limit is exceeded.
    """
    logger.info(
        f"Chat request — session: {body.session_id[:8]}... | "
        f"stream: {body.stream} | question: {body.question[:60]}..."
    )

    if body.stream:
        # SSE streaming — tokens arrive word by word
        return StreamingResponse(
            stream_chat_response(
                question=body.question,
                session_id=body.session_id,
                db=db,
                use_cache=body.use_cache,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # disables Nginx buffering
            },
        )

    # Full response — collect all tokens then return JSON
    full_response = ""
    cached = False
    latency_ms: float | None = None

    async for event in stream_chat_response(
        question=body.question,
        session_id=body.session_id,
        db=db,
        use_cache=body.use_cache,
    ):
        data = _json.loads(event.replace("data: ", "").strip())

        if data["type"] == "token":
            full_response += data["content"]
        elif data["type"] == "done":
            cached = data.get("cached", False)
            latency_ms = data.get("latency_ms")
        elif data["type"] == "error":
            raise APIError.llm_failed()

    response_data: dict = {"response": full_response, "cached": cached}
    if latency_ms is not None:
        response_data["latency_ms"] = latency_ms

    return JSONResponse(content=response_data)
