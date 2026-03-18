"""src/ingestion/linkedin_loader.py

LinkedIn profile data loader.

Reads CSV files exported from LinkedIn and converts them
to plain text for chunking and embedding.

LinkedIn export instructions:
    LinkedIn → Me → Settings & Privacy → Data Privacy →
    Get a copy of your data → Request archive →
    Place extracted CSVs in data/linkedin/

Files used:
    Profile.csv                 — headline, summary, industry, location
    Recommendations_Received.csv — written recommendations (VISIBLE only)

Responsibility: load and format LinkedIn CSV data. Nothing else.
Does NOT: chunk, embed, or store documents.

Typical usage:
    from src.ingestion.linkedin_loader import load_linkedin_documents

    documents = await load_linkedin_documents()
"""

import csv

from src.core.logger import logger
from utils.paths import get_data_path

# Directory containing LinkedIn CSV exports
LINKEDIN_DIR = get_data_path("linkedin")


def _read_csv(filename: str) -> list[dict]:
    """Read a LinkedIn CSV export file into a list of row dicts.

    Uses utf-8-sig encoding to strip the BOM character that
    LinkedIn adds to CSV exports.

    Args:
        filename: CSV filename within data/linkedin/.

    Returns:
        List of row dicts. Empty list if file does not exist.
    """
    path = LINKEDIN_DIR / filename
    if not path.exists():
        logger.warning(f"LinkedIn CSV not found: {path} — skipping")
        return []

    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _format_profile(profile: dict) -> str:
    """Format the Profile CSV row as plain text.

    Includes professional headline, summary, industry, location,
    and website URLs. Skips personal fields (birth date, address)
    that are not relevant for the chatbot.

    Args:
        profile: Row dict from Profile.csv.

    Returns:
        Formatted plain text string ready for chunking.
        Empty string if profile has no meaningful content.
    """
    parts = []

    # Full name for context
    first = profile.get("First Name", "").strip()
    last = profile.get("Last Name", "").strip()
    if first or last:
        parts.append(f"Name: {first} {last}".strip())

    if profile.get("Headline"):
        parts.append(f"Headline: {profile['Headline'].strip()}")

    if profile.get("Summary"):
        parts.append(f"Summary: {profile['Summary'].strip()}")

    if profile.get("Industry"):
        parts.append(f"Industry: {profile['Industry'].strip()}")

    if profile.get("Geo Location"):
        parts.append(f"Location: {profile['Geo Location'].strip()}")

    # Parse website URLs — stored as "[TYPE:url,TYPE:url]"
    websites_raw = profile.get("Websites", "").strip()
    if websites_raw and websites_raw not in ("", "[]"):
        # Strip brackets and split by comma
        websites_clean = websites_raw.strip("[]")
        urls = [
            entry.split(":")[-1].strip()
            for entry in websites_clean.split(",")
            if ":" in entry
        ]
        # Reconstruct full URLs — split on ":" removes "https"
        raw_entries = websites_clean.split(",")
        full_urls = []
        for entry in raw_entries:
            # Format is "TYPE:https://..." — join everything after first colon
            parts_split = entry.strip().split(":", 1)
            if len(parts_split) == 2:
                full_urls.append(parts_split[1].strip())
        if full_urls:
            parts.append(f"Websites: {', '.join(full_urls)}")

    return "\n".join(parts)


def _format_recommendation(rec: dict) -> str:
    """Format a single recommendation row as plain text.

    Only includes recommendations with Status == 'VISIBLE'.
    Skips hidden or pending recommendations.

    Args:
        rec: Row dict from Recommendations_Received.csv.

    Returns:
        Formatted plain text string ready for chunking.
        Empty string if recommendation is not visible or has no text.
    """
    # Skip non-visible recommendations
    if rec.get("Status", "").strip().upper() != "VISIBLE":
        return ""

    # Skip empty recommendations
    if not rec.get("Text", "").strip():
        return ""

    parts = []

    first = rec.get("First Name", "").strip()
    last = rec.get("Last Name", "").strip()
    if first or last:
        parts.append(f"Recommendation from: {first} {last}".strip())

    if rec.get("Job Title"):
        parts.append(f"Their role: {rec['Job Title'].strip()}")

    if rec.get("Company"):
        parts.append(f"Company: {rec['Company'].strip()}")

    parts.append(f'"{rec["Text"].strip()}"')

    return "\n".join(parts)


async def load_linkedin_documents() -> list[dict]:
    """Load and format all LinkedIn CSV exports as plain text documents.

    Reads Profile and Recommendations_Received CSVs from
    data/linkedin/ and formats each as plain text ready for
    chunking and embedding.

    Missing CSV files are skipped with a warning — partial
    exports are handled gracefully.

    Returns:
        List of dicts with keys: text, source, source_id.
        source is always 'linkedin'.
        source_id identifies the originating record.

    Example:
        >>> docs = await load_linkedin_documents()
        >>> docs[0].keys()
        dict_keys(['text', 'source', 'source_id'])
    """
    documents = []

    # Profile — single document from first row
    profiles = _read_csv("Profile.csv")
    if profiles:
        # LinkedIn Profile.csv always has exactly one row
        text = _format_profile(profiles[0])
        if text.strip():
            documents.append(
                {
                    "text": text,
                    "source": "linkedin",
                    "source_id": "linkedin-profile",
                }
            )
        logger.info("Loaded LinkedIn profile")
    else:
        logger.warning("Profile.csv empty or missing")

    # Recommendations — one document per visible recommendation
    recommendations = _read_csv("Recommendations_Received.csv")
    visible_count = 0
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
            visible_count += 1

    logger.info(
        f"Loaded {visible_count} visible recommendations "
        f"({len(recommendations) - visible_count} skipped)"
    )

    logger.info(f"Total LinkedIn documents loaded: {len(documents)}")
    return documents
