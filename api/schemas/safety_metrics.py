"""Schemas for safety metrics responses."""

from pydantic import BaseModel, Field


class SafetyMetricsResponse(BaseModel):
    """Current in-process safety counters since process start."""

    started_at: str = Field(description="UTC timestamp when the counters started.")
    uptime_seconds: int = Field(
        description="Seconds since the current process started collecting metrics."
    )
    totals: dict[str, int] = Field(
        description="Top-level safety totals such as requests and answers returned."
    )
    response_routes: dict[str, int] = Field(
        description="Counts of final response routes such as llm or pre_router."
    )
    pre_router_categories: dict[str, int] = Field(
        description="Counts for pre-router categories such as identity or private."
    )
    pre_router_reasons: dict[str, int] = Field(
        description="Counts for specific pre-router decisions."
    )
    retrieval_gate_reasons: dict[str, int] = Field(
        description="Counts for retrieval confidence gate fallbacks."
    )
    fallback_reasons: dict[str, int] = Field(
        description="Counts for last-resort runtime fallbacks."
    )
