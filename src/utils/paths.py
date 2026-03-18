"""
Project path utilities.

Provides a single PROJECT_ROOT constant and helper functions
for resolving paths relative to the project root.

Responsibility: resolve paths. Nothing else.
"""

from pathlib import Path

# Resolved from this file's location — works regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_data_path(*parts: str) -> Path:
    """Resolve a path relative to the project data directory.

    Args:
        *parts: Path components relative to data/.

    Returns:
        Absolute path under the project data directory.

    Example:
        >>> get_data_path("linkedin", "Recommendations.csv")
        PosixPath('/project/data/linkedin/Recommendations.csv')
    """
    return PROJECT_ROOT / "data" / Path(*parts)
