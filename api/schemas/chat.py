"""
Pydantic schemas for the chat endpoint.

Defines request and response shapes for POST /v1/chat.
All fields are validated by FastAPI before reaching the route handler.

Responsibility: define API contracts. Nothing else.
Does NOT: handle requests, call the LLM, or manage sessions.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /v1/chat.

    Attributes:
        question: User question to answer. Must be non-empty.
        session_id: Browser session identifier for conversation history.
            Generate a UUID in the frontend and persist in localStorage.
            Pass the same ID across requests to maintain multi-turn context.
        use_cache: Whether to check and populate the semantic cache.
            Defaults to True. Set False during testing to always hit the LLM.
    """

    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["What projects has Chitrank built?"],
        description="Question to ask about Chitrank",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["session-abc123"],
        description="Browser session ID for conversation history",
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use semantic response cache",
    )
