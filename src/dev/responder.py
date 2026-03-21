"""Seeded local response generation for development mode."""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.dev.seed_data import SEED_CONTACT_EMAIL

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


def build_seeded_response(messages: list[dict]) -> str:
    """Build a deterministic local response from prompt context."""
    question = _extract_question(messages)
    context = _extract_context(messages)
    if not context:
        return _fallback_response()

    chunks = _parse_context_chunks(context)
    question_tokens = set(_tokenize(question))

    if question_tokens & _CONTACT_TERMS:
        return f"In dev mode, the fictional seed profile points people to {SEED_CONTACT_EMAIL}."

    if question_tokens & _PROJECT_TERMS:
        return _project_response(chunks)

    if question_tokens & _SKILL_TERMS:
        return _skills_response(chunks)

    if question_tokens & _FEEDBACK_TERMS:
        return _feedback_response(chunks)

    if question_tokens & _EXPERIENCE_TERMS:
        return _experience_response(chunks)

    return _general_response(chunks)


def _extract_question(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", "")).strip()
    return ""


def _extract_context(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") != "system":
            continue

        content = str(message.get("content", ""))
        start_marker = "--- CONTEXT ---"
        end_marker = "--- END CONTEXT ---"

        if start_marker not in content or end_marker not in content:
            continue

        start = content.index(start_marker) + len(start_marker)
        end = content.index(end_marker)
        return content[start:end].strip()

    return ""


def _parse_context_chunks(context: str) -> list[dict]:
    pattern = re.compile(
        r"\[(?P<index>\d+)\] Source: (?P<source>[^\n]+)\n(?P<body>.*?)(?=\n\n\[\d+\] Source: |\Z)",
        re.DOTALL,
    )
    chunks = []
    for match in pattern.finditer(context):
        chunks.append(
            {
                "source": match.group("source").strip(),
                "content": match.group("body").strip(),
            }
        )
    return chunks


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


def _project_response(chunks: list[dict]) -> str:
    titles = _prefixed_values(chunks, "Project: ")
    technologies = _split_csv(_prefixed_values(chunks, "Technologies: "))

    if not titles:
        return _general_response(chunks)

    title_text = ", ".join(titles[:4])
    response = (
        f"In dev mode, the fictional seed profile shows projects like {title_text}."
    )

    if technologies:
        response += (
            " The fictional project context highlights work with "
            f"{', '.join(technologies[:8])}."
        )

    return response


def _skills_response(chunks: list[dict]) -> str:
    technologies = _split_csv(_prefixed_values(chunks, "Technologies: "))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Languages: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Frameworks: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Platforms: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "AI and Data: ")))
    technologies.extend(_split_csv(_prefixed_values(chunks, "Tools: ")))
    technologies = _dedupe(technologies)

    if not technologies:
        return _general_response(chunks)

    return (
        "In dev mode, the fictional seed profile highlights a stack including "
        f"{', '.join(technologies[:10])}."
    )


def _feedback_response(chunks: list[dict]) -> str:
    authors = _prefixed_values(chunks, "From: ")
    authors.extend(_prefixed_values(chunks, "Recommendation from: "))
    quotes = _quoted_lines(chunks)

    response = (
        "In dev mode, the fictional seeded recommendations describe the profile "
        "as collaborative and dependable."
    )

    if authors:
        response += f" The sample feedback comes from {', '.join(authors[:3])}."

    if quotes:
        response += f" Example: {quotes[0]}"

    return response


def _experience_response(chunks: list[dict]) -> str:
    years = _first_match(
        chunks,
        re.compile(r"\b\d+\+?\s+years? of experience\b", re.IGNORECASE),
    )
    roles = _prefixed_values(chunks, "Role: ")
    companies = _prefixed_values(chunks, "Company: ")

    parts = [
        "In dev mode, the fictional seeded profile describes a Senior Software Engineer."
    ]

    if years:
        parts.append(f"It mentions {years}.")

    if roles:
        parts.append(f"Sample roles include {', '.join(roles[:3])}.")

    if companies:
        parts.append(
            f"The fictional work history spans contexts like {', '.join(companies[:3])}."
        )

    return " ".join(parts)


def _general_response(chunks: list[dict]) -> str:
    highlights = []
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
                return (
                    "In dev mode, the fictional seeded context suggests: "
                    + " ".join(highlights)
                )

    return _fallback_response()


def _quoted_lines(chunks: Iterable[dict]) -> list[str]:
    quotes: list[str] = []
    for chunk in chunks:
        for line in chunk["content"].splitlines():
            cleaned = line.strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                quotes.append(cleaned)
    return quotes


def _first_match(chunks: Iterable[dict], pattern: re.Pattern[str]) -> str | None:
    for chunk in chunks:
        match = pattern.search(chunk["content"])
        if match:
            return match.group(0)
    return None


def _fallback_response() -> str:
    return (
        "In dev mode, no matching fictional seeded answer was found. "
        f"You can still use {SEED_CONTACT_EMAIL} as the contact fallback."
    )
