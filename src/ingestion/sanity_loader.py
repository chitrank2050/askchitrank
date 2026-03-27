"""
Sanity CMS data loader.

Fetches Project and Testimonial documents from Sanity CMS
via the HTTP API and converts them to plain text for chunking.

Document types:
    Project     — title, role, company, overview, vision,
                  technologies, contribution, liveUrl, githubUrl
    Testimonial — author, role, quote, linkedinUrl

Responsibility: fetch and format Sanity CMS data. Nothing else.
Does NOT: chunk, embed, or store documents.

Typical usage:
    from src.ingestion.sanity_loader import load_sanity_documents

    documents = await load_sanity_documents()
"""

import httpx

from src.core.config import settings
from src.core.logger import logger
from src.dev.seed_data import SEED_SANITY_PROJECTS, SEED_SANITY_TESTIMONIALS

# Sanity CDN base URL for GROQ queries
_SANITY_API_BASE = (
    f"https://{settings.SANITY_PROJECT_ID}.api.sanity.io"
    f"/v{settings.SANITY_API_VERSION}/data/query/{settings.SANITY_DATASET}"
)

# Fetch all projects with full detail fields
_PROJECTS_QUERY = """
*[_type == "project"] | order(_createdAt desc) {
    _id,
    title,
    role,
    company,
    overview,
    vision,
    technologies,
    contribution,
    liveUrl,
    githubUrl
}
"""

# Fetch all testimonials
_TESTIMONIALS_QUERY = """
*[_type == "testimonial"] | order(_createdAt desc) {
    _id,
    author,
    role,
    quote,
    linkedinUrl
}
"""


def _format_project(project: dict) -> str:
    """Convert a Project document to plain text for chunking.

    Formats all meaningful fields into a structured plain text block
    that provides full context about the project to the LLM.
    Excludes image fields — not useful for text retrieval.

    Args:
        project: Raw project dict from Sanity API response.

    Returns:
        Formatted plain text string ready for chunking.
        Empty string if project has no meaningful content.
    """
    parts = []

    if project.get("title"):
        parts.append(f"Project: {project['title']}")
    if project.get("company"):
        parts.append(f"Company: {project['company']}")
    if project.get("role"):
        parts.append(f"Role: {project['role']}")
    if project.get("overview"):
        parts.append(f"Overview: {project['overview']}")
    if project.get("vision"):
        parts.append(f"Vision: {project['vision']}")
    if project.get("technologies"):
        techs = ", ".join(project["technologies"])
        parts.append(f"Technologies: {techs}")
    if project.get("contribution"):
        contributions = "\n- ".join(project["contribution"])
        parts.append(f"Contributions:\n- {contributions}")
    if project.get("liveUrl"):
        parts.append(f"Live URL: {project['liveUrl']}")
    if project.get("githubUrl"):
        parts.append(f"GitHub: {project['githubUrl']}")

    return "\n".join(parts)


def _project_keywords(project: dict) -> list[str]:
    """Extract compact retrieval hints from a project document."""
    raw_values = [
        project.get("title", ""),
        project.get("company", ""),
        project.get("role", ""),
    ]
    raw_values.extend(project.get("technologies") or [])

    seen: set[str] = set()
    keywords: list[str] = []

    for value in raw_values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(cleaned)

    return keywords


def _build_project_documents(project: dict) -> list[dict]:
    """Create bounded semantic documents for project retrieval."""
    documents: list[dict] = []
    source_id = project["_id"]
    keywords = _project_keywords(project)
    keyword_line = f"Keywords: {', '.join(keywords)}" if keywords else ""
    techs = ", ".join(project.get("technologies") or [])

    overview_parts = []
    if project.get("title"):
        overview_parts.append(f"Project: {project['title']}")
    overview_parts.append("Evidence Type: project")
    overview_parts.append(
        "Useful for queries about: projects, role, company, technologies, product work"
    )
    if project.get("company"):
        overview_parts.append(f"Company: {project['company']}")
    if project.get("role"):
        overview_parts.append(f"Role: {project['role']}")
    if techs:
        overview_parts.append(f"Technologies: {techs}")
    if keyword_line:
        overview_parts.append(keyword_line)
    overview_prefix = "\n".join(overview_parts)

    overview_body_parts = []
    if project.get("overview"):
        overview_body_parts.append(f"Overview: {project['overview']}")
    if project.get("vision"):
        overview_body_parts.append(f"Vision: {project['vision']}")

    documents.append(
        {
            "text": "\n".join(
                part
                for part in [overview_prefix, "\n".join(overview_body_parts).strip()]
                if part.strip()
            ),
            "source": "sanity",
            "source_id": f"{source_id}#overview",
            "chunk_prefix": overview_prefix,
        }
    )

    contributions = project.get("contribution") or []
    if contributions:
        contribution_parts = []
        if project.get("title"):
            contribution_parts.append(f"Project: {project['title']}")
        contribution_parts.append("Evidence Type: project-contribution")
        contribution_parts.append(
            "Useful for queries about: responsibilities, impact, delivery, execution"
        )
        if project.get("role"):
            contribution_parts.append(f"Role: {project['role']}")
        if techs:
            contribution_parts.append(f"Technologies: {techs}")
        if keyword_line:
            contribution_parts.append(keyword_line)
        contribution_parts.append("Key Contributions:")
        contribution_prefix = "\n".join(contribution_parts)
        contribution_text = "\n- ".join(contributions)

        documents.append(
            {
                "text": f"{contribution_prefix}\n- {contribution_text}",
                "source": "sanity",
                "source_id": f"{source_id}#contributions",
                "chunk_prefix": contribution_prefix,
            }
        )

    if project.get("liveUrl") or project.get("githubUrl"):
        link_parts = []
        if project.get("title"):
            link_parts.append(f"Project: {project['title']}")
        link_parts.append("Evidence Type: project-links")
        link_parts.append("Useful for queries about: live demo, repository, links")
        if project.get("liveUrl"):
            link_parts.append(f"Live URL: {project['liveUrl']}")
        if project.get("githubUrl"):
            link_parts.append(f"GitHub: {project['githubUrl']}")
        if keyword_line:
            link_parts.append(keyword_line)
        link_prefix = "\n".join(link_parts)

        documents.append(
            {
                "text": link_prefix,
                "source": "sanity",
                "source_id": f"{source_id}#links",
                "chunk_prefix": link_prefix,
            }
        )

    return documents


def _format_testimonial(testimonial: dict) -> str:
    """Convert a Testimonial document to plain text for chunking.

    Args:
        testimonial: Raw testimonial dict from Sanity API response.

    Returns:
        Formatted plain text string ready for chunking.
        Empty string if testimonial has no meaningful content.
    """
    parts = []

    if testimonial.get("quote"):
        parts.append(f'Testimonial: "{testimonial["quote"]}"')
    if testimonial.get("author"):
        parts.append(f"From: {testimonial['author']}")
    if testimonial.get("role"):
        parts.append(f"Role: {testimonial['role']}")

    return "\n".join(parts)


def _build_testimonial_document(testimonial: dict) -> dict:
    """Create a retrieval-friendly testimonial document."""
    parts = ["Evidence Type: testimonial"]
    parts.append("Useful for queries about: feedback, collaboration, communication")
    if testimonial.get("author"):
        parts.append(f"From: {testimonial['author']}")
    if testimonial.get("role"):
        parts.append(f"Role: {testimonial['role']}")
    prefix = "\n".join(parts)
    body = ""
    if testimonial.get("quote"):
        body = f'Testimonial: "{testimonial["quote"]}"'

    return {
        "text": "\n".join(part for part in [prefix, body] if part),
        "source": "testimonial",
        "source_id": testimonial["_id"],
        "chunk_prefix": prefix,
    }


async def _fetch(query: str) -> list[dict]:
    """Execute a GROQ query against the Sanity HTTP API.

    Args:
        query: GROQ query string to execute.

    Returns:
        List of document dicts returned by the query.
        Empty list if query returns no results.

    Raises:
        httpx.HTTPError: If the API request fails or returns non-200.
    """
    headers = {}
    if settings.SANITY_API_TOKEN:
        # API token required for draft documents and private datasets
        headers["Authorization"] = f"Bearer {settings.SANITY_API_TOKEN}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            _SANITY_API_BASE,
            params={"query": query},
            headers=headers,
        )
        response.raise_for_status()
        return response.json().get("result", [])


async def load_sanity_documents() -> list[dict]:
    """Fetch all documents from Sanity CMS and format as plain text.

    Fetches Projects and Testimonials, formats each document as
    plain text, and returns a list of dicts ready for chunking
    and embedding.

    Returns:
        List of dicts with keys: text, source, source_id.
        source is always 'sanity'.
        source_id is the Sanity document _id.

    Raises:
        httpx.HTTPError: If any Sanity API request fails.

    Example:
        >>> docs = await load_sanity_documents()
        >>> docs[0].keys()
        dict_keys(['text', 'source', 'source_id'])
    """
    documents = []

    if settings.DEV_MODE:
        logger.info("DEV_MODE enabled — using seeded Sanity documents")
        projects = SEED_SANITY_PROJECTS
        testimonials = SEED_SANITY_TESTIMONIALS
    else:
        # Fetch and format projects
        projects = await _fetch(_PROJECTS_QUERY)
        logger.info(f"Fetched {len(projects)} projects from Sanity")

        # Fetch and format testimonials
        testimonials = await _fetch(_TESTIMONIALS_QUERY)
        logger.info(f"Fetched {len(testimonials)} testimonials from Sanity")

    for project in projects:
        documents.extend(_build_project_documents(project))

    for testimonial in testimonials:
        text = _format_testimonial(testimonial)
        if text.strip():
            documents.append(_build_testimonial_document(testimonial))

    logger.info(f"Total Sanity documents loaded: {len(documents)}")
    return documents
