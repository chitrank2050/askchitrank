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

    # Fetch and format projects
    projects = await _fetch(_PROJECTS_QUERY)
    logger.info(f"Fetched {len(projects)} projects from Sanity")

    for project in projects:
        text = _format_project(project)
        if text.strip():
            documents.append(
                {
                    "text": text,
                    "source": "sanity",
                    "source_id": project["_id"],
                }
            )

    # Fetch and format testimonials
    testimonials = await _fetch(_TESTIMONIALS_QUERY)
    logger.info(f"Fetched {len(testimonials)} testimonials from Sanity")

    for testimonial in testimonials:
        text = _format_testimonial(testimonial)
        if text.strip():
            documents.append(
                {
                    "text": text,
                    "source": "sanity",
                    "source_id": testimonial["_id"],
                }
            )

    logger.info(f"Total Sanity documents loaded: {len(documents)}")
    return documents
