"""
Chat endpoint — streams RAG responses via Server-Sent Events.

Accepts a user question and session ID, runs the full RAG pipeline,
and streams the response token by token as SSE events.

Endpoints:
    POST /v1/chat

SSE event format:
    data: {"type": "token", "content": "..."}  — response token
    data: {"type": "done", "cached": bool}     — stream complete
    data: {"type": "error", "message": "..."}  — pipeline error
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.chat import ChatRequest
from api.utils.rate_limit import limiter
from src.chat.stream import stream_chat_response
from src.core.logger import logger
from src.db.connection import get_db

router = APIRouter()


@router.post(
    "/chat",
    summary="Ask a question about Chitrank",
    description=(
        "Streams a RAG-powered response via Server-Sent Events. "
        "Each token is yielded as it arrives from the LLM. "
        "Pass the same session_id across requests to maintain conversation context."
    ),
    response_class=StreamingResponse,
)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a RAG response for the user question.

    Runs the full pipeline: embed → cache check → retrieve →
    prompt → stream LLM → store cache → store conversation.

    Args:
        request: FastAPI request — required by slowapi rate limiter.
        body: Validated ChatRequest with question and session_id.
        db: Database session injected by FastAPI dependency.

    Returns:
        StreamingResponse with SSE content type.
        Tokens stream as they arrive from the LLM.
    """
    logger.info(
        f"Chat request — session: {body.session_id[:8]}... | "
        f"question: {body.question[:60]}..."
    )

    return StreamingResponse(
        stream_chat_response(
            question=body.question,
            session_id=body.session_id,
            db=db,
            use_cache=body.use_cache,
        ),
        media_type="text/event-stream",
        headers={
            # Required headers for SSE
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disables Nginx buffering
        },
    )
