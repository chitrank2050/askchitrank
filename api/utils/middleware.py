"""Custom middleware for the FastAPI application."""

from uuid import uuid4

from fastapi import Request


async def add_request_id(request: Request, call_next):
    """Add unique request ID to every request for tracing."""
    request_id = str(uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
