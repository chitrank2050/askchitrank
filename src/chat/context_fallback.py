"""Deterministic fallback answers built directly from retrieved context."""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.chat.safety import get_contact_email, get_subject_name

_PROJECT_TERMS = {"project", "projects", "built", "build", "portfolio", "app"}
_SKILL_TERMS = {
    "skill",
    "skills",
    "stack",
    "tech",
    "technology",
    "technologies",
    "framework",
    "frameworks",
}
_FEEDBACK_TERMS = {
    "testimonial",
    "testimonials",
    "feedback",
    "recommendation",
    "recommendations",
    "colleague",
    "colleagues",
    "manager",
    "say",
}
_EXPERIENCE_TERMS = {
    "experience",
    "years",
    "worked",
    "career",
    "role",
    "roles",
    "company",
    "companies",
}
_CONTACT_TERMS = {"contact", "email", "reach", "connect"}


def build_context_fallback_response(question: str, chunks: list[dict]) -> str | None:
    """Build a safe answer directly from retrieved chunks when generation fails."""
    if not chunks:
        return None

    question_tokens = set(_tokenize(question))

    if question_tokens & _CONTACT_TERMS:
        return f"You can reach {get_subject_name()} at {get_contact_email()}."

    if question_tokens & _PROJECT_TERMS:
        return _project_response(chunks)

    if question_tokens & _SKILL_TERMS:
        return _skills_response(chunks)

    if question_tokens & _FEEDBACK_TERMS:
        return _feedback_response(chunks)

    if question_tokens & _EXPERIENCE_TERMS:
        return _experience_response(chunks)

    return _general_response(chunks)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+#.-]*", text.lower())


def _prefixed_values(chunks: Iterable[dict], prefix: str) -> list[str]:
    values: list[str] = []
    for chunk in chunks:
        for line in chunk["content"].splitlines():
            if line.startswith(prefix):
                value = line.removeprefix(prefix).strip()
                if value:
                    values.append(value)
    return _dedupe(values)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []

    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)

    return unique


def _split_csv(values: Iterable[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for item in value.split(","):
            cleaned = item.strip(" -")
            if cleaned:
                items.append(cleaned)
    return _dedupe(items)


def _quoted_lines(chunks: Iterable[dict]) -> list[str]:
    quotes: list[str] = []
    for chunk in chunks:
        for line in chunk["content"].splitlines():
            cleaned = line.strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                quotes.append(cleaned)
            elif cleaned.startswith("Testimonial: "):
                quote = cleaned.removeprefix("Testimonial: ").strip()
                if quote:
                    quotes.append(quote)
    return _dedupe(quotes)


def _first_match(chunks: Iterable[dict], pattern: re.Pattern[str]) -> str | None:
    for chunk in chunks:
        match = pattern.search(chunk["content"])
        if match:
            return match.group(0)
    return None


def _project_response(chunks: list[dict]) -> str | None:
    titles = _prefixed_values(chunks, "Project: ")
    technologies = _split_csv(_prefixed_values(chunks, "Technologies: "))
    subject_name = get_subject_name()

    if not titles and not technologies:
        return None

    parts: list[str] = []
    if titles:
        parts.append(f"{subject_name} has built projects like {', '.join(titles[:4])}.")
    if technologies:
        parts.append(
            "Relevant technologies in the retrieved portfolio context include "
            f"{', '.join(technologies[:8])}."
        )
    return " ".join(parts)


def _skills_response(chunks: list[dict]) -> str | None:
    technologies = _split_csv(_prefixed_values(chunks, "Technologies: "))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Languages: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Frameworks: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Platforms: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "AI and Data: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Tools: ")))
    technologies = _dedupe(technologies)

    if not technologies:
        return None

    return (
        f"{get_subject_name()}'s public portfolio context highlights skills including "
        f"{', '.join(technologies[:10])}."
    )


def _feedback_response(chunks: list[dict]) -> str | None:
    authors = _prefixed_values(chunks, "From: ")
    authors.extend(_prefixed_values(chunks, "Recommendation from: "))
    authors = _dedupe(authors)
    quotes = _quoted_lines(chunks)

    if not authors and not quotes:
        return None

    parts = [f"Public feedback describes {get_subject_name()} positively."]
    if authors:
        parts.append(f"Sample feedback comes from {', '.join(authors[:3])}.")
    if quotes:
        parts.append(f"Example: {quotes[0]}")
    return " ".join(parts)


def _experience_response(chunks: list[dict]) -> str | None:
    years = _first_match(
        chunks,
        re.compile(r"\b\d+\+?\s+years? of experience\b", re.IGNORECASE),
    )
    roles = _prefixed_values(chunks, "Role: ")
    companies = _prefixed_values(chunks, "Company: ")
    subject_name = get_subject_name()

    if not years and not roles and not companies:
        return None

    parts: list[str] = []
    if years:
        parts.append(f"{subject_name} has {years}.")
    else:
        parts.append(
            f"The retrieved portfolio context describes {subject_name}'s professional experience."
        )

    if roles:
        parts.append(f"Sample roles include {', '.join(roles[:3])}.")
    if companies:
        parts.append(
            f"The retrieved portfolio context references companies or work contexts like {', '.join(companies[:3])}."
        )

    return " ".join(parts)


def _general_response(chunks: list[dict]) -> str | None:
    highlights: list[str] = []
    for chunk in chunks:
        for line in chunk["content"].splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if cleaned.startswith(
                ("Evidence Type:", "Keywords:", "Useful for queries about:")
            ):
                continue
            highlights.append(cleaned)
            if len(highlights) == 2:
                return "Based on the retrieved portfolio context: " + " ".join(
                    highlights
                )

    if highlights:
        return f"Based on the retrieved portfolio context: {highlights[0]}"

    return None
