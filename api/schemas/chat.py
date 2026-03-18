"""
Pydantic schemas for the chat endpoint.

Defines request and response shapes for POST /v1/chat.
All fields are validated by FastAPI before reaching the route handler.

Responsibility: define API contracts. Nothing else.
Does NOT: handle requests, call the LLM, or manage sessions.
"""

import re

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request body for POST /v1/chat.

    Attributes:
        question: User question to answer. Must be non-empty and meaningful.
        session_id: Browser session identifier for conversation history.
            Generate a UUID in the frontend and persist in localStorage.
            Pass the same ID across requests to maintain multi-turn context.
        use_cache: Whether to check and populate the semantic cache.
            Defaults to True. Set False during testing to always hit the LLM.
        stream: Whether to stream response via SSE or return full JSON.
            Defaults to True. Set False for simple integrations.
    """

    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
        examples=["What projects has Chitrank built?"],
        description="Question to ask. Must be at least 2 characters.",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="Browser session UUID. Generate once and persist in localStorage.",
    )
    use_cache: bool = Field(
        default=True,
        description="Use semantic response cache. Set false during testing.",
    )
    stream: bool = Field(
        default=True,
        description="Stream tokens via SSE (true) or return full JSON response (false).",
    )

    @field_validator("question", mode="before")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Strip whitespace and reject empty or whitespace-only questions.

        Args:
            v: Raw question string from request.

        Returns:
            Stripped question string.

        Raises:
            ValueError: If question is empty after stripping.
        """
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty or whitespace only.")
        return v

    @field_validator("session_id", mode="before")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Strip whitespace and validate session ID format.

        Accepts any non-empty string — UUIDs are recommended but not
        required to allow flexibility in frontend implementation.

        Args:
            v: Raw session ID from request.

        Returns:
            Stripped session ID.

        Raises:
            ValueError: If session ID is empty after stripping.
        """
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Session ID cannot be empty.")
        # Block obvious injection attempts in session ID
        if re.search(r"[<>\"'%;()&+]", v):
            raise ValueError(
                "Session ID contains invalid characters. "
                "Use a UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )
        return v

    model_config = {
        "extra": "forbid",  # reject unexpected fields
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }
