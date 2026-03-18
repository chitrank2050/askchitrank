"""src/ingestion/sanity_loader.py

Sanity CMS data loader.

Fetches Project and Testimonial documents from Sanity CMS
via the HTTP API and converts them to plain text for chunking.

Responsibility: fetch and format Sanity CMS data. Nothing else.
Does NOT: chunk, embed, or store documents.

Typical usage:
    from src.ingestion.sanity_loader import load_sanity_documents

    documents = await load_sanity_documents()
"""

import httpx

from src.core.config import settings
from src.core.logger import logger

# Sanity CDN base URL — read-only, no auth required for public data
SANITY_API_BASE = (
    f"https://{settings.SANITY_PROJECT_ID}.api.sanity.io"
    f"/v{settings.SANITY_API_VERSION}/data/query/{settings.SANITY_DATASET}"
)

# GROQ query — fetch all projects with full detail
PROJECTS_QUERY = """
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

# GROQ query — fetch all testimonials
TESTIMONIALS_QUERY = """
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

    Formats all meaningful fields into a structured text block
    that provides full context about the project to the LLM.

    Args:
        project: Raw project dict from Sanity API.

    Returns:
        Formatted plain text string ready for chunking.
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
        testimonial: Raw testimonial dict from Sanity API.

    Returns:
        Formatted plain text string ready for chunking.
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
    """Execute a GROQ query against the Sanity API.

    Args:
        query: GROQ query string.

    Returns:
        List of document dicts returned by the query.

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    headers = {}
    if settings.SANITY_API_TOKEN:
        headers["Authorization"] = f"Bearer {settings.SANITY_API_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            SANITY_API_BASE,
            params={"query": query},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("result", [])


async def load_sanity_documents() -> list[dict]:
    """Fetch all documents from Sanity CMS and format as plain text.

    Fetches Projects and Testimonials, formats each as plain text,
    and returns a list of dicts ready for chunking and embedding.

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
    projects = await _fetch(PROJECTS_QUERY)
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
    testimonials = await _fetch(TESTIMONIALS_QUERY)
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
