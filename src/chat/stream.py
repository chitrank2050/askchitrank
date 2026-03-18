"""
Streaming response handler.

Orchestrates the full RAG query pipeline and streams the LLM response
to the client via Server-Sent Events (SSE).

Pipeline per request:
    1. Embed the user question (Voyage AI)
    2. Check semantic cache — return cached response if similar question exists
    3. Search knowledge base — retrieve top K relevant chunks
    4. Build prompt — system prompt + context + question
    5. Stream LLM response token by token (Groq)
    6. Collect full response and store in cache
    7. Store conversation turn in conversations table

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
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.groq_client import stream_response
from src.chat.prompt import build_messages
from src.core.logger import logger
from src.db.models import Conversation
from src.ingestion.embedder import embed_query
from src.retrieval.cache import find_cached_response, store_cached_response
from src.retrieval.search import search_knowledge_base


async def stream_chat_response(
    question: str,
    session_id: str,
    db: AsyncSession,
    use_cache: bool = True,
) -> AsyncGenerator[str, None]:
    """Orchestrate the RAG pipeline and stream the response as SSE events.

    Runs the full pipeline: embed → cache check → retrieve → prompt →
    stream LLM → store cache → store conversation.

    Yields Server-Sent Events in the format:
        data: {"type": "token", "content": "..."}
        data: {"type": "done", "cached": false}
        data: {"type": "error", "message": "..."}

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
    try:
        # ── Step 1: Embed the question ─────────────────────────────────────
        logger.info(f"Processing question: {question[:60]}...")
        query_embedding = await embed_query(question)

        # ── Step 2: Check semantic cache ───────────────────────────────────
        if use_cache:
            cached = await find_cached_response(query_embedding, db)
            if cached:
                logger.info("Cache hit — returning cached response")

                # Store conversation turn even for cached responses
                await _store_conversation(question, cached["response"], session_id, db)

                # Stream cached response token by token for consistent UX
                # Users shouldn't know or care whether response is cached
                words = cached["response"].split(" ")
                for word in words:
                    yield _sse_event("token", word + " ")

                yield _sse_event("done", "", cached=True)
                return

        # ── Step 3: Search knowledge base ──────────────────────────────────
        chunks = await search_knowledge_base(query_embedding, db)

        if not chunks:
            logger.warning("No chunks found for question — returning fallback")
            fallback = (
                "I don't have enough information to answer that. "
                "You can reach Chitrank directly at chitrank2050@gmail.com."
            )
            yield _sse_event("token", fallback)
            yield _sse_event("done", "", cached=False)
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

        async for token in stream_response(messages):
            full_response += token
            yield _sse_event("token", token)

        logger.info(f"Streamed response — {len(full_response)} chars")

        # ── Step 6: Store in cache ─────────────────────────────────────────
        if use_cache and full_response:
            chunk_ids = [c["id"] for c in chunks]
            await store_cached_response(
                question=question,
                question_embedding=query_embedding,
                response=full_response,
                source_chunk_ids=chunk_ids,
                db=db,
            )

        # ── Step 7: Store conversation turn ────────────────────────────────
        if full_response:
            await _store_conversation(question, full_response, session_id, db)

        yield _sse_event("done", "", cached=False)

    except Exception as e:
        logger.error(f"Chat pipeline failed: {e}")
        yield _sse_event("error", str(e))


def _sse_event(
    event_type: str,
    content: str,
    cached: bool = False,
) -> str:
    """Format a Server-Sent Event string.

    All events follow the same JSON structure so the frontend
    can parse them consistently regardless of event type.

    Args:
        event_type: One of 'token', 'done', or 'error'.
        content: Token text for 'token' events, error message for 'error'.
        cached: Whether this response came from the cache. Only relevant
            for 'done' events.

    Returns:
        SSE-formatted string with trailing newlines.

    Example:
        >>> _sse_event("token", "Hello")
        'data: {"type": "token", "content": "Hello"}\\n\\n'
    """
    payload: dict = {"type": event_type, "content": content}

    if event_type == "done":
        payload["cached"] = cached

    return f"data: {json.dumps(payload)}\n\n"


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
