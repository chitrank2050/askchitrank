"""Safety routing, canned responses, and lightweight metrics for chat."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Literal

from src.core.config import settings
from src.core.logger import logger
from src.dev.seed_data import SEED_CONTACT_EMAIL, SEED_PERSON_NAME

RouteCategory = Literal[
    "normal",
    "identity",
    "private",
    "explicit",
    "prompt_injection",
    "off_topic",
]

ResponseRoute = Literal[
    "pre_router",
    "cache_hit",
    "llm",
    "dev_seeded",
    "confidence_fallback",
    "error_fallback",
]

_PORTFOLIO_TERMS = {
    "chitrank",
    "portfolio",
    "project",
    "projects",
    "skill",
    "skills",
    "experience",
    "resume",
    "work",
    "worked",
    "career",
    "background",
    "linkedin",
    "testimonial",
    "testimonials",
    "recommendation",
    "recommendations",
    "contact",
    "email",
    "hire",
    "role",
    "roles",
    "company",
    "companies",
    "stack",
    "technology",
    "technologies",
    "built",
    "build",
}

_OFF_TOPIC_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bweather\b",
        r"\btemperature\b",
        r"\bforecast\b",
        r"\bsports?\b",
        r"\bmatch\b",
        r"\bscore\b",
        r"\brecipe\b",
        r"\bcook\b",
        r"\btravel\b",
        r"\bflight\b",
        r"\bhotel\b",
        r"\bbitcoin\b",
        r"\bcrypto\b",
        r"\bstock\b",
        r"\bshare price\b",
        r"\bpolitics?\b",
        r"\belection\b",
        r"\btranslate\b",
        r"\bpoem\b",
        r"\bjoke\b",
        r"\bmovie\b",
        r"\bcricket\b",
        r"\bfootball\b",
        r"\bipl\b",
        r"\bnba\b",
    )
]
_PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bignore (all )?(previous|prior|earlier) instructions\b",
        r"\bsystem prompt\b",
        r"\bdeveloper message\b",
        r"\breveal (your )?(prompt|instructions)\b",
        r"\bshow (me )?(your )?(prompt|hidden instructions)\b",
        r"\bjailbreak\b",
        r"\bbypass (your )?(rules|guardrails|safety)\b",
        r"\bact as\b",
    )
]
_EXPLICIT_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bsex\b",
        r"\bsexual\b",
        r"\bnude\b",
        r"\bnaked\b",
        r"\bporn\b",
        r"\bexplicit\b",
        r"\bfuck(?:ing)?\b",
        r"\bblowjob\b",
        r"\bboobs?\b",
        r"\bpenis\b",
        r"\bvagina\b",
    )
]
_ASSISTANT_IDENTITY_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bwho are you\b",
        r"\bwhat are you\b",
        r"\bare you (an )?(ai|bot|assistant)\b",
        r"\bwhat do you do\b",
    )
]
_PERSONHOOD_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bare you chitrank\b",
        r"\bare you him\b",
        r"\bis this chitrank\b",
        r"\bare you the real (one|person|chitrank)\b",
        r"\bcan i talk to chitrank\b",
    )
]
_COMPENSATION_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bhow much .*?\b(earn|make|get paid)\b",
        r"\b(salary|ctc|compensation|income|net worth|package)\b",
        r"\bwhat does .*?\b(earn|make|get paid)\b",
    )
]
_SENSITIVE_PERSONAL_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bphone number\b",
        r"\bmobile number\b",
        r"\bwhatsapp\b",
        r"\bhome address\b",
        r"\bhouse address\b",
        r"\bwhere does .* live\b",
        r"\bdate of birth\b",
        r"\bage\b",
        r"\brelationship\b",
        r"\bgirlfriend\b",
        r"\bwife\b",
        r"\breligion\b",
        r"\bpolitical\b",
    )
]


@dataclass(frozen=True)
class PreRouteDecision:
    """Outcome of the cheap pre-routing safety pass."""

    category: RouteCategory
    reason: str
    should_bypass_rag: bool
    response: str | None = None


class SafetyMetricsRegistry:
    """In-process counters for safety decisions and response routes."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(UTC)
        self._totals: Counter[str] = Counter()
        self._response_routes: Counter[str] = Counter()
        self._pre_router_categories: Counter[str] = Counter()
        self._pre_router_reasons: Counter[str] = Counter()
        self._retrieval_gate_reasons: Counter[str] = Counter()
        self._fallback_reasons: Counter[str] = Counter()

    def record_request(self) -> None:
        self._increment(self._totals, "requests_total")

    def record_response_route(self, route: ResponseRoute) -> None:
        with self._lock:
            self._totals["answers_returned_total"] += 1
            self._response_routes[route] += 1
        logger.info("Safety metric | event=response_route route={}", route)

    def record_pre_router(self, category: RouteCategory, reason: str) -> None:
        with self._lock:
            self._pre_router_categories[category] += 1
            self._pre_router_reasons[reason] += 1
        logger.info(
            "Safety metric | event=pre_router category={} reason={}",
            category,
            reason,
        )

    def record_retrieval_gate(self, reason: str) -> None:
        self._increment(self._retrieval_gate_reasons, reason)
        logger.info("Safety metric | event=retrieval_gate reason={}", reason)

    def record_fallback(self, reason: str) -> None:
        self._increment(self._fallback_reasons, reason)
        logger.info("Safety metric | event=fallback reason={}", reason)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime_seconds = int((datetime.now(UTC) - self._started_at).total_seconds())
            return {
                "started_at": self._started_at.isoformat(),
                "uptime_seconds": uptime_seconds,
                "totals": dict(sorted(self._totals.items())),
                "response_routes": dict(sorted(self._response_routes.items())),
                "pre_router_categories": dict(
                    sorted(self._pre_router_categories.items())
                ),
                "pre_router_reasons": dict(sorted(self._pre_router_reasons.items())),
                "retrieval_gate_reasons": dict(
                    sorted(self._retrieval_gate_reasons.items())
                ),
                "fallback_reasons": dict(sorted(self._fallback_reasons.items())),
            }

    def _increment(self, counter: Counter[str], key: str) -> None:
        with self._lock:
            counter[key] += 1


def get_contact_email() -> str:
    """Return the public contact email for the active runtime mode."""
    return SEED_CONTACT_EMAIL if settings.DEV_MODE else settings.CONTACT_EMAIL


def get_subject_name() -> str:
    """Return the person name represented by the active runtime mode."""
    return SEED_PERSON_NAME if settings.DEV_MODE else "Chitrank"


def route_question(question: str) -> PreRouteDecision:
    """Classify obvious unsupported or special-case questions cheaply."""
    normalized = _normalize(question)
    tokens = set(_tokenize(normalized))

    if _matches_any(_PROMPT_INJECTION_PATTERNS, normalized):
        return PreRouteDecision(
            category="prompt_injection",
            reason="prompt_override_attempt",
            should_bypass_rag=True,
            response=_prompt_injection_response(),
        )

    if _matches_any(_EXPLICIT_PATTERNS, normalized):
        return PreRouteDecision(
            category="explicit",
            reason="explicit_content",
            should_bypass_rag=True,
            response=_explicit_response(),
        )

    if _matches_any(_PERSONHOOD_PATTERNS, normalized):
        return PreRouteDecision(
            category="identity",
            reason="personhood_confusion",
            should_bypass_rag=True,
            response=_personhood_response(),
        )

    if _matches_any(_ASSISTANT_IDENTITY_PATTERNS, normalized):
        return PreRouteDecision(
            category="identity",
            reason="assistant_identity",
            should_bypass_rag=True,
            response=_assistant_identity_response(),
        )

    if _matches_any(_COMPENSATION_PATTERNS, normalized):
        return PreRouteDecision(
            category="private",
            reason="compensation",
            should_bypass_rag=True,
            response=_compensation_response(),
        )

    if _matches_any(_SENSITIVE_PERSONAL_PATTERNS, normalized):
        return PreRouteDecision(
            category="private",
            reason="sensitive_personal_data",
            should_bypass_rag=True,
            response=_private_info_response(),
        )

    if tokens and not (tokens & _PORTFOLIO_TERMS) and _looks_off_topic(normalized):
        return PreRouteDecision(
            category="off_topic",
            reason="unsupported_topic",
            should_bypass_rag=True,
            response=_off_topic_response(),
        )

    return PreRouteDecision(
        category="normal",
        reason="normal_rag",
        should_bypass_rag=False,
    )


def build_low_confidence_response(reason: str) -> str:
    """Return the always-answer fallback when retrieval is too weak."""
    if reason == "empty_results":
        return (
            "I don't have any verified portfolio context for that yet. "
            f"I can help with {get_subject_name()}'s projects, experience, skills, "
            f"testimonials, or public contact details. You can also reach out at {get_contact_email()}."
        )

    return (
        "I don't have enough verified portfolio information to answer that confidently. "
        f"I can still help with {get_subject_name()}'s projects, experience, skills, "
        f"testimonials, or public contact details. You can also reach out at {get_contact_email()}."
    )


def build_pipeline_fallback_response(has_partial_response: bool = False) -> str:
    """Return a graceful final answer when generation fails."""
    if has_partial_response:
        return "I don't want to guess beyond the verified portfolio information I have."

    return (
        "I couldn't complete a fully verified answer just now, so I don't want to guess. "
        f"I can still help with {get_subject_name()}'s projects, experience, skills, "
        f"or public contact details. You can also reach out at {get_contact_email()}."
    )


def get_safety_metrics_snapshot() -> dict[str, Any]:
    """Expose the current safety counters for the API layer."""
    return safety_metrics.snapshot()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+#.-]*", text)


def _matches_any(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _looks_off_topic(text: str) -> bool:
    return any(pattern.search(text) for pattern in _OFF_TOPIC_PATTERNS)


def _assistant_identity_response() -> str:
    if settings.DEV_MODE:
        return (
            "I'm the dev-mode version of Ask Chitrank. "
            f"I'm an AI assistant using fictional seeded data about {SEED_PERSON_NAME} "
            "so local testing does not spend real tokens."
        )

    return (
        "I'm Ask Chitrank, the AI assistant on Chitrank's portfolio site. "
        "I can help with his public projects, experience, skills, and profile."
    )


def _personhood_response() -> str:
    if settings.DEV_MODE:
        return (
            "No. I'm not Chitrank, and in dev mode I'm not speaking for a real person. "
            f"I'm the local test version of the assistant using fictional seeded data about {SEED_PERSON_NAME}."
        )

    return (
        "No. I'm not Chitrank himself. I'm Ask Chitrank, an AI assistant that answers "
        "questions about his public portfolio content. "
        f"If you want to reach him directly, use {get_contact_email()}."
    )


def _compensation_response() -> str:
    if settings.DEV_MODE:
        return (
            "I don't expose compensation details in dev mode. The local setup uses "
            f"fictional seeded data about {SEED_PERSON_NAME}, and it does not include salary information."
        )

    return (
        "I don't have verified public information about Chitrank's compensation. "
        f"I can help with his experience, projects, and skills, or you can reach him at {get_contact_email()}."
    )


def _private_info_response() -> str:
    return (
        "I only share professional, portfolio-relevant public information here. "
        f"I don't provide private personal details. If you need a public point of contact, use {get_contact_email()}."
    )


def _explicit_response() -> str:
    return (
        "I can't help with explicit or sexual requests. "
        f"I'm here for professional questions about {get_subject_name()}'s projects, experience, and skills."
    )


def _prompt_injection_response() -> str:
    return (
        "I can't reveal internal prompts or ignore my safety rules. "
        f"I can still help with questions about {get_subject_name()}'s public portfolio content."
    )


def _off_topic_response() -> str:
    return (
        "I'm here to answer questions about "
        f"{get_subject_name()}'s projects, experience, skills, testimonials, and public profile. "
        "If you want, ask about one of those areas."
    )


safety_metrics = SafetyMetricsRegistry()


__all__ = [
    "PreRouteDecision",
    "build_low_confidence_response",
    "build_pipeline_fallback_response",
    "get_contact_email",
    "get_safety_metrics_snapshot",
    "get_subject_name",
    "route_question",
    "safety_metrics",
]
