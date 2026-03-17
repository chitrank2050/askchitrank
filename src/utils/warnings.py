import warnings
from typing import TypedDict


class WarningEntry(TypedDict):
    message: str
    category: type[Warning]
    reason: str


# Registry of all suppressed warnings in the project.
SUPPRESSED_WARNINGS: list[WarningEntry] = []


def suppress_known_warnings() -> None:
    """Suppress all known/acknowledged warnings in one call."""
    for entry in SUPPRESSED_WARNINGS:
        warnings.filterwarnings(
            "ignore",
            message=entry["message"],
            category=entry["category"],
        )
