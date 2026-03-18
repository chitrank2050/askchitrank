"""
LinkedIn profile data loader.

Reads CSV files exported from LinkedIn and converts them
to plain text for chunking and embedding.

LinkedIn export instructions:
    LinkedIn → Me → Settings & Privacy → Data Privacy →
    Get a copy of your data → Request archive →
    Place extracted CSVs in data/linkedin/

Files used:
    Recommendations.csv  — written recommendations from colleagues
    Positions.csv        — work history
    Skills.csv           — endorsed skills

Responsibility: load and format LinkedIn CSV data. Nothing else.
Does NOT: chunk, embed, or store documents.

Typical usage:
    from src.ingestion.linkedin_loader import load_linkedin_documents

    documents = await load_linkedin_documents()
"""

import csv
from pathlib import Path

from src.core.logger import logger
from src.utils.paths import get_data_path

# Directory containing LinkedIn CSV exports
LINKEDIN_DIR = get_data_path("linkedin")


def _read_csv(filename: str) -> list[dict]:
    """Read a LinkedIn CSV export file into a list of row dicts.

    Args:
        filename: CSV filename within data/linkedin/.

    Returns:
        List of row dicts. Empty list if file does not exist.
    """
    path = LINKEDIN_DIR / filename
    if not path.exists():
        logger.warning(f"LinkedIn CSV not found: {path} — skipping")
        return []

    with Path.open(path, encoding="utf-8-sig") as f:  # utf-8-sig strips BOM
        reader = csv.DictReader(f)
        return list(reader)


def _format_recommendation(rec: dict) -> str:
    """Format a single recommendation row as plain text.

    Args:
        rec: Row dict from Recommendations.csv.

    Returns:
        Formatted plain text string.
    """
    parts = []

    if rec.get("First Name") and rec.get("Last Name"):
        name = f"{rec['First Name']} {rec['Last Name']}".strip()
        parts.append(f"Recommendation from: {name}")
    if rec.get("Company"):
        parts.append(f"Company: {rec['Company']}")
    if rec.get("Job Title"):
        parts.append(f"Their role: {rec['Job Title']}")
    if rec.get("Text"):
        parts.append(f'"{rec["Text"]}"')

    return "\n".join(parts)


def _format_position(pos: dict) -> str:
    """Format a single position row as plain text.

    Args:
        pos: Row dict from Positions.csv.

    Returns:
        Formatted plain text string.
    """
    parts = []

    if pos.get("Title"):
        parts.append(f"Role: {pos['Title']}")
    if pos.get("Company Name"):
        parts.append(f"Company: {pos['Company Name']}")
    if pos.get("Started On") and pos.get("Finished On"):
        parts.append(f"Period: {pos['Started On']} — {pos['Finished On']}")
    elif pos.get("Started On"):
        parts.append(f"Period: {pos['Started On']} — Present")
    if pos.get("Description"):
        parts.append(f"Description: {pos['Description']}")

    return "\n".join(parts)


def _format_skills(skills: list[dict]) -> str:
    """Format all skills rows as a single plain text block.

    Skills are short — grouping them into one document avoids
    creating dozens of tiny chunks.

    Args:
        skills: List of row dicts from Skills.csv.

    Returns:
        Formatted plain text string with all skills listed.
    """
    skill_names = [
        s.get("Name", "").strip() for s in skills if s.get("Name", "").strip()
    ]
    if not skill_names:
        return ""
    return "Skills: " + ", ".join(skill_names)


async def load_linkedin_documents() -> list[dict]:
    """Load and format all LinkedIn CSV exports as plain text.

    Reads Recommendations, Positions, and Skills CSVs from
    data/linkedin/ and formats each as plain text ready for
    chunking and embedding.

    Missing CSV files are skipped with a warning — partial
    exports are handled gracefully.

    Returns:
        List of dicts with keys: text, source, source_id.
        source is always 'linkedin'.
        source_id identifies the originating CSV file.

    Example:
        >>> docs = await load_linkedin_documents()
        >>> docs[0].keys()
        dict_keys(['text', 'source', 'source_id'])
    """
    documents = []

    # Recommendations — one document per recommendation
    recommendations = _read_csv("Recommendations.csv")
    logger.info(f"Loaded {len(recommendations)} LinkedIn recommendations")
    for i, rec in enumerate(recommendations):
        text = _format_recommendation(rec)
        if text.strip():
            documents.append(
                {
                    "text": text,
                    "source": "linkedin",
                    "source_id": f"linkedin-recommendation-{i}",
                }
            )

    # Positions — one document per role
    positions = _read_csv("Positions.csv")
    logger.info(f"Loaded {len(positions)} LinkedIn positions")
    for i, pos in enumerate(positions):
        text = _format_position(pos)
        if text.strip():
            documents.append(
                {
                    "text": text,
                    "source": "linkedin",
                    "source_id": f"linkedin-position-{i}",
                }
            )

    # Skills — all grouped into one document
    skills = _read_csv("Skills.csv")
    logger.info(f"Loaded {len(skills)} LinkedIn skills")
    skills_text = _format_skills(skills)
    if skills_text:
        documents.append(
            {
                "text": skills_text,
                "source": "linkedin",
                "source_id": "linkedin-skills",
            }
        )

    logger.info(f"Total LinkedIn documents loaded: {len(documents)}")
    return documents
