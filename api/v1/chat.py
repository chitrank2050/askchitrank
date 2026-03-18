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

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
    response_model=None,
)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse | JSONResponse:
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
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Full response — wait for complete answer then return JSON
        full_response = ""
        cached = False

        async for event in stream_chat_response(
            question=body.question,
            session_id=body.session_id,
            db=db,
            use_cache=body.use_cache,
        ):
            import json as _json

            data = _json.loads(event.replace("data: ", "").strip())
            if data["type"] == "token":
                full_response += data["content"]
            elif data["type"] == "done":
                cached = data.get("cached", False)
            elif data["type"] == "error":
                raise HTTPException(status_code=500, detail=data["content"])

        return JSONResponse(content={"response": full_response, "cached": cached})
