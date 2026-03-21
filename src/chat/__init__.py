"""
Chat pipeline package.

Orchestrates the full RAG query pipeline — from user question
to streamed LLM response.

Pipeline:
    1. route_question()        — cheap safety pre-router
    2. embed_query()           — Voyage AI, 'query' input type
    3. find_cached_response()  — semantic cache lookup
    4. search_knowledge_base() — pgvector similarity search
    5. build_messages()        — system prompt + context + question
    6. stream_response()       — Groq LLM streaming
    7. store_cached_response() — populate cache for future requests
    8. _store_conversation()   — persist conversation history

Typical usage:
    from src.chat.stream import stream_chat_response

    async for event in stream_chat_response(question, session_id, db):
        yield event  # SSE event strings
"""

from .stream import stream_chat_response

__all__ = ["stream_chat_response"]
