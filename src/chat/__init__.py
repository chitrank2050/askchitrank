"""
Chat pipeline package.

Orchestrates the full RAG query pipeline — from user question
to streamed LLM response.

Pipeline:
    1. embed_query()           — Voyage AI, 'query' input type
    2. find_cached_response()  — semantic cache lookup
    3. search_knowledge_base() — pgvector similarity search
    4. build_messages()        — system prompt + context + question
    5. stream_response()       — Groq LLM streaming
    6. store_cached_response() — populate cache for future requests
    7. _store_conversation()   — persist conversation history

Typical usage:
    from src.chat.stream import stream_chat_response

    async for event in stream_chat_response(question, session_id, db):
        yield event  # SSE event strings
"""

from .stream import stream_chat_response

__all__ = ["stream_chat_response"]
