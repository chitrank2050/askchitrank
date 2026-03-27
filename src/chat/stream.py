"""
Streaming response handler.

Orchestrates the full RAG query pipeline and streams the LLM response
to the client via Server-Sent Events (SSE).

Pipeline per request:
    1. Cheap safety pre-router for obvious unsupported questions
    2. Embed the user question (Voyage AI)
    3. Check semantic cache — return cached response if similar question exists
    4. Search knowledge base — retrieve top K relevant chunks
    5. Assess retrieval confidence before calling the LLM
    6. Build prompt — system prompt + context + question
    7. Stream LLM response token by token (Groq)
    8. Collect full response and store in cache
    9. Store conversation turn in conversations table

This module is the single entry point for the chat API endpoint.
All other chat modules (prompt, groq_client) are called from here.

Responsibility: orchestrate the RAG pipeline and stream output. Nothing else.
Does NOT: define prompt structure, manage embeddings, or handle HTTP directly.

Typical usage:
    from src.chat.stream import stream_chat_response

    async for event in stream_chat_response(question, session_id, db):
        yield event
"""

import json
import re
import time
import traceback
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.context_fallback import build_context_fallback_response
from src.chat.groq_client import stream_response
from src.chat.prompt import build_messages
from src.chat.safety import (
    build_low_confidence_response,
    build_pipeline_fallback_response,
    route_question,
    safety_metrics,
)
from src.core.config import settings
from src.core.logger import logger
from src.db.models import Conversation
from src.dev.seed_data import get_seeded_context_chunks
from src.ingestion.embedder import embed_query
from src.retrieval.cache import (
    find_cached_response,
    find_exact_cached_response,
    store_cached_response,
)
from src.retrieval.search import assess_retrieval_confidence, search_knowledge_base


async def stream_chat_response(
    question: str,
    session_id: str,
    db: AsyncSession | None,
    use_cache: bool = True,
) -> AsyncGenerator[str, None]:
    """Orchestrate the RAG pipeline and stream the response as SSE events.

    Runs the full pipeline: embed → cache check → retrieve → prompt →
    stream LLM → store cache → store conversation.

    Yields Server-Sent Events in the format:
        data: {"type": "token", "content": "..."}
        data: {"type": "done", "cached": false}

    The pipeline prefers returning a safe fallback answer over emitting
    an error event, so callers should normally expect only token/done.

    Args:
        question: User question text.
        session_id: Browser session ID for conversation history.
        db: Active async database session.
        use_cache: Whether to check and populate the semantic cache.
            Set False during testing to always hit the LLM.

    Yields:
        SSE-formatted strings ready to send to the client.

    Example:
        >>> async for event in stream_chat_response("What projects?", "session-1", db):
        ...     print(event)
        data: {"type": "token", "content": "Chitrank"}
        data: {"type": "token", "content": " has"}
        data: {"type": "done", "cached": false}
    """
    safety_metrics.record_request()
    pipeline_start = time.perf_counter()

    try:
        pre_route = route_question(question)
        if pre_route.should_bypass_rag and pre_route.response:
            logger.info(
                "Pre-router handled question — category: {} | reason: {}",
                pre_route.category,
                pre_route.reason,
            )
            safety_metrics.record_pre_router(pre_route.category, pre_route.reason)
            safety_metrics.record_response_route("pre_router")
            await _emit_answer(
                question=question,
                response=pre_route.response,
                session_id=session_id,
                db=db,
            )
            latency = (time.perf_counter() - pipeline_start) * 1000
            async for event in _stream_text_response(
                pre_route.response, cached=False, latency_ms=latency
            ):
                yield event
            return

        if db is None and not settings.DEV_MODE:
            logger.warning(
                "Database unavailable for chat — returning degraded fallback"
            )
            safety_metrics.record_fallback("database_unavailable")
            safety_metrics.record_response_route("error_fallback")
            fallback = build_pipeline_fallback_response()
            latency = (time.perf_counter() - pipeline_start) * 1000
            async for event in _stream_text_response(
                fallback, cached=False, latency_ms=latency
            ):
                yield event
            return

        if settings.DEV_MODE and db is None:
            logger.info("DEV_MODE without database — serving seeded chat response")
            messages = build_messages(
                question=question,
                chunks=get_seeded_context_chunks(),
                conversation_history=None,
            )
            full_response = ""
            async for token in stream_response(messages):
                full_response += token
                yield _sse_event("token", token)
            if not full_response.strip():
                fallback = build_pipeline_fallback_response()
                safety_metrics.record_fallback("empty_dev_seeded_response")
                safety_metrics.record_response_route("error_fallback")
                latency = (time.perf_counter() - pipeline_start) * 1000
                async for event in _stream_text_response(
                    fallback, cached=False, latency_ms=latency
                ):
                    yield event
                return
            safety_metrics.record_response_route("dev_seeded")
            latency = (time.perf_counter() - pipeline_start) * 1000
            yield _sse_event("done", "", cached=False, latency_ms=latency)
            return

        # ── Step 0.5: Exact match cache check ──────────────────────────────
        if use_cache and db is not None:
            exact_cached = await find_exact_cached_response(question, db)
            if exact_cached:
                logger.info(
                    "Exact cache hit — returning cached response without embedding"
                )

                # Store conversation turn even for exact cached responses
                await _emit_answer(
                    question=question,
                    response=exact_cached["response"],
                    session_id=session_id,
                    db=db,
                )
                safety_metrics.record_response_route("cache_hit")

                latency = (time.perf_counter() - pipeline_start) * 1000
                async for event in _stream_text_response(
                    exact_cached["response"], cached=True, latency_ms=latency
                ):
                    yield event
                return

        # ── Step 1: Embed the question ─────────────────────────────────────
        logger.info(f"Processing question: {question[:60]}...")
        query_embedding = await embed_query(question)

        # ── Step 2: Check semantic cache ───────────────────────────────────
        if use_cache and db is not None:
            cached = await find_cached_response(query_embedding, db)
            if cached:
                logger.info("Cache hit — returning cached response")

                # Store conversation turn even for cached responses
                await _emit_answer(
                    question=question,
                    response=cached["response"],
                    session_id=session_id,
                    db=db,
                )
                safety_metrics.record_response_route("cache_hit")

                # Stream cached response token by token for consistent UX
                # Users shouldn't know or care whether response is cached
                latency = (time.perf_counter() - pipeline_start) * 1000
                async for event in _stream_text_response(
                    cached["response"], cached=True, latency_ms=latency
                ):
                    yield event
                return

        assert db is not None

        # ── Step 3: Search knowledge base ──────────────────────────────────
        chunks = await search_knowledge_base(
            query_embedding=query_embedding,
            db=db,
            query_text=question,
        )

        confidence = assess_retrieval_confidence(question, chunks)
        if not confidence.is_confident:
            logger.warning(
                "Retrieval confidence too low — reason: {} | top similarity: {} | "
                "best coverage: {}",
                confidence.reason,
                confidence.top_similarity,
                confidence.best_query_coverage,
            )
            safety_metrics.record_retrieval_gate(confidence.reason)
            safety_metrics.record_response_route("confidence_fallback")
            fallback = build_low_confidence_response(confidence.reason)
            await _emit_answer(
                question=question,
                response=fallback,
                session_id=session_id,
                db=db,
            )
            latency = (time.perf_counter() - pipeline_start) * 1000
            async for event in _stream_text_response(
                fallback, cached=False, latency_ms=latency
            ):
                yield event
            return

        logger.debug(
            f"Retrieved {len(chunks)} chunks — top similarity: {chunks[0]['similarity']}"
        )

        # ── Step 4: Build prompt ───────────────────────────────────────────
        # Fetch recent conversation history for multi-turn context
        history = await _get_conversation_history(session_id, db, limit=6)
        messages = build_messages(
            question=question,
            chunks=chunks,
            conversation_history=history,
        )

        # ── Step 5: Stream LLM response ────────────────────────────────────
        full_response = ""
        generation_failed = False
        try:
            async for token in stream_response(messages):
                full_response += token
                yield _sse_event("token", token)
        except Exception as exc:
            generation_failed = True
            logger.error("LLM streaming failed: {}", exc)

        if generation_failed or not full_response.strip():
            safety_metrics.record_fallback("generation_failure")
            safety_metrics.record_response_route("error_fallback")
            fallback = ""
            if not full_response.strip():
                fallback = build_context_fallback_response(question, chunks) or ""
            if not fallback:
                fallback = build_pipeline_fallback_response(
                    has_partial_response=bool(full_response.strip())
                )
            streamed_fallback = (
                fallback if not full_response.strip() else f" {fallback}"
            )
            full_response += streamed_fallback
            for token in _iter_text_tokens(streamed_fallback):
                yield _sse_event("token", token)
            await _emit_answer(
                question=question,
                response=full_response.strip(),
                session_id=session_id,
                db=db,
            )
            latency = (time.perf_counter() - pipeline_start) * 1000
            yield _sse_event("done", "", cached=False, latency_ms=latency)
            return

        logger.info(f"Streamed response — {len(full_response)} chars")
        safety_metrics.record_response_route("llm")

        # ── Step 6: Store in cache ─────────────────────────────────────────
        if use_cache and full_response and db is not None:
            chunk_ids = [c["id"] for c in chunks]
            try:
                await store_cached_response(
                    question=question,
                    question_embedding=query_embedding,
                    response=full_response,
                    source_chunk_ids=chunk_ids,
                    db=db,
                )
            except Exception as exc:
                logger.warning("Failed to store response cache entry: {}", exc)

        # ── Step 7: Store conversation turn ────────────────────────────────
        if full_response and db is not None:
            try:
                await _store_conversation(question, full_response, session_id, db)
            except Exception as exc:
                logger.warning("Failed to store conversation turn: {}", exc)

        latency = (time.perf_counter() - pipeline_start) * 1000
        yield _sse_event("done", "", cached=False, latency_ms=latency)

    except Exception as e:
        logger.error(
            "Chat pipeline failed before completion: {}\n{}", e, traceback.format_exc()
        )
        safety_metrics.record_fallback("pipeline_failure")
        safety_metrics.record_response_route("error_fallback")
        fallback = build_pipeline_fallback_response()
        await _emit_answer(
            question=question,
            response=fallback,
            session_id=session_id,
            db=db,
        )
        latency = (time.perf_counter() - pipeline_start) * 1000
        async for event in _stream_text_response(
            fallback, cached=False, latency_ms=latency
        ):
            yield event


def _sse_event(
    event_type: str,
    content: str,
    cached: bool = False,
    latency_ms: float | None = None,
) -> str:
    """Format a Server-Sent Event string.

    All events follow the same JSON structure so the frontend
    can parse them consistently regardless of event type.

    Args:
        event_type: One of 'token', 'done', or 'error'.
        content: Token text for 'token' events, error message for 'error'.
        cached: Whether this response came from the cache. Only relevant
            for 'done' events.
        latency_ms: Total pipeline latency in milliseconds. Only included
            in 'done' events when provided.

    Returns:
        SSE-formatted string with trailing newlines.

    Example:
        >>> _sse_event("token", "Hello")
        'data: {"type": "token", "content": "Hello"}\\n\\n'
        >>> _sse_event("done", "", cached=False, latency_ms=142.5)
        'data: {"type": "done", "content": "", "cached": false, "latency_ms": 142.5}\\n\\n'
    """
    payload: dict = {"type": event_type, "content": content}

    if event_type == "done":
        payload["cached"] = cached
        if latency_ms is not None:
            payload["latency_ms"] = round(latency_ms, 1)

    return f"data: {json.dumps(payload)}\n\n"


def _iter_text_tokens(text: str) -> list[str]:
    """Split text into stream-friendly chunks while preserving spaces."""
    return re.findall(r"\s*\S+\s*", text)


async def _stream_text_response(
    text: str,
    cached: bool,
    latency_ms: float | None = None,
) -> AsyncGenerator[str, None]:
    """Yield a complete text response as SSE token events plus done."""
    for token in _iter_text_tokens(text):
        yield _sse_event("token", token)

    yield _sse_event("done", "", cached=cached, latency_ms=latency_ms)


async def _emit_answer(
    question: str,
    response: str,
    session_id: str,
    db: AsyncSession | None,
) -> None:
    """Persist assistant answers when a database session is available."""
    if not response or db is None:
        return

    try:
        await _store_conversation(question, response, session_id, db)
    except Exception as exc:
        logger.warning("Failed to store conversation turn: {}", exc)


async def _store_conversation(
    question: str,
    response: str,
    session_id: str,
    db: AsyncSession,
) -> None:
    """Store a conversation turn — user question and assistant response.

    Stores both the user message and assistant response as separate rows
    in the conversations table for multi-turn conversation history.

    Args:
        question: User question text.
        response: Full assistant response text.
        session_id: Browser session identifier.
        db: Active async database session.
    """
    now = datetime.now(UTC)

    db.add(
        Conversation(
            session_id=session_id,
            role="user",
            content=question,
            created_at=now,
        )
    )
    db.add(
        Conversation(
            session_id=session_id,
            role="assistant",
            content=response,
            created_at=now,
        )
    )
    await db.commit()
    logger.debug(f"Stored conversation turn — session: {session_id[:8]}...")


async def _get_conversation_history(
    session_id: str,
    db: AsyncSession,
    limit: int = 6,
) -> list[dict]:
    """Fetch recent conversation history for a session.

    Returns the last N messages ordered chronologically so the LLM
    has context from the current conversation. Limited to avoid
    exceeding token limits.

    Args:
        session_id: Browser session identifier.
        db: Active async database session.
        limit: Maximum number of recent messages to return. Default 6
            (3 turns of user + assistant). Must be even to keep pairs.

    Returns:
        List of message dicts in OpenAI format:
        [{"role": "user"|"assistant", "content": "..."}]
        Empty list if no history exists.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    # Reverse to chronological order — we fetched desc for limit efficiency
    rows = list(reversed(rows))

    return [{"role": row.role, "content": row.content} for row in rows]
