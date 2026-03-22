"""
Local query expansion via synonym groups.

Expands query tokens to include related terms, improving recall
for short or ambiguous queries without any API calls.

Responsibility: expand query tokens. Nothing else.
Does NOT: embed, search, or call external services.

Typical usage:
    from src.retrieval.synonyms import expand_tokens

    tokens = {"tech", "stack"}
    expanded = expand_tokens(tokens)
    # → {"tech", "stack", "technology", "technologies", "tools"}
"""

from __future__ import annotations

# Each set is a group of interchangeable terms.
# Expansion is bidirectional: any term maps to all others in its group.
_SYNONYM_GROUPS: list[set[str]] = [
    {"tech", "technology", "technologies", "stack", "tools"},
    {"frontend", "react", "nextjs", "next.js", "ui", "tailwind", "css"},
    {"backend", "api", "server", "fastapi", "node"},
    {"ml", "machine-learning", "ai", "deep-learning", "model"},
    {"devops", "ci/cd", "docker", "kubernetes", "deployment", "deploy"},
    {"job", "role", "position", "employment"},
    {
        "feedback",
        "testimonial",
        "testimonials",
        "recommendation",
        "recommendations",
        "review",
    },
    {"project", "projects", "portfolio", "product", "app"},
    {"experience", "career", "worked", "work"},
    {"skill", "skills", "expertise", "proficiency"},
    {"education", "degree", "university", "college"},
    {"contact", "email", "hire", "reach"},
]

# Build reverse index at import time: token → full group set
_TOKEN_TO_GROUP: dict[str, set[str]] = {}
for _group in _SYNONYM_GROUPS:
    for _token in _group:
        _TOKEN_TO_GROUP[_token] = _group


def expand_tokens(tokens: set[str]) -> set[str]:
    """Expand a set of query tokens with synonyms.

    Returns the union of the original tokens and any synonym
    group members matched by the input tokens.
    """
    expanded = set(tokens)
    for token in tokens:
        group = _TOKEN_TO_GROUP.get(token)
        if group:
            expanded |= group
    return expanded
