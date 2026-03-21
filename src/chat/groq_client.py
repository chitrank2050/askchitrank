"""
Groq LLM API client.

Handles all communication with the Groq API — both standard
responses and streaming. Uses the Groq Python SDK which follows
the OpenAI SDK interface.

Groq is used for its free tier and exceptional inference speed
(10-20x faster than GPU-based providers on the same models).
The client is designed to be provider-agnostic — swapping to
Claude or GPT requires only changing this file.

Responsibility: call the LLM API. Nothing else.
Does NOT: build prompts, manage cache, or handle streaming to clients.

Typical usage:
    from src.chat.groq_client import get_response, stream_response

    # Standard response
    response = await get_response(messages)

    # Streaming response
    async for token in stream_response(messages):
        print(token, end="", flush=True)
"""

from collections.abc import AsyncGenerator
from typing import Any, cast

from groq import AsyncGroq

from src.core.config import settings
from src.core.logger import logger
from src.dev.responder import build_seeded_response

# Groq async client — initialised once, reused across calls
_client = None if settings.DEV_MODE else AsyncGroq(api_key=settings.GROQ_API_KEY)


async def get_response(messages: list[dict[str, Any]]) -> str:
    """Get a complete response from the Groq LLM.

    Sends the message list to Groq and waits for the full response.
    Use this for non-streaming use cases like cache population.

    Args:
        messages: List of message dicts in OpenAI chat format.
            Must include a system message and at least one user message.

    Returns:
        Full response text from the LLM.

    Raises:
        groq.APIError: If the Groq API call fails.
        groq.RateLimitError: If the free tier rate limit is exceeded.

    Example:
        >>> response = await get_response(messages)
        >>> print(response[:100])
        Chitrank has built several projects including...
    """
    if settings.DEV_MODE:
        logger.debug("Returning seeded dev response")
        return build_seeded_response(cast(Any, messages))

    logger.debug(f"Calling Groq API — model: {settings.GROQ_MODEL}")

    assert _client is not None

    completion = await _client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=cast(Any, messages),
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,  # low temperature — factual answers
        stream=False,
    )

    response = completion.choices[0].message.content or ""

    logger.debug(
        f"Groq response — tokens: {completion.usage.total_tokens if completion.usage else 'unknown'}"
    )

    return response


async def stream_response(
    messages: list[dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """Stream a response from the Groq LLM token by token.

    Uses Groq's streaming API to yield response tokens as they arrive.
    This enables real-time streaming to the frontend via Server-Sent Events.

    Args:
        messages: List of message dicts in OpenAI chat format.

    Yields:
        Individual text tokens as they stream from the API.
        Empty strings are filtered out.

    Raises:
        groq.APIError: If the Groq API call fails.
        groq.RateLimitError: If the free tier rate limit is exceeded.

    Example:
        >>> async for token in stream_response(messages):
        ...     print(token, end="", flush=True)
        Chitrank has built...
    """
    if settings.DEV_MODE:
        logger.debug("Streaming seeded dev response")
        seeded_response = build_seeded_response(cast(Any, messages))
        for token in seeded_response.split(" "):
            if token:
                yield token + " "
        return

    logger.debug(f"Streaming Groq response — model: {settings.GROQ_MODEL}")

    assert _client is not None

    stream = await _client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=cast(Any, messages),
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        stream=True,
    )

    async for chunk in stream:
        # Extract token text — delta.content is None for the final chunk
        token = chunk.choices[0].delta.content
        if token:
            yield token
