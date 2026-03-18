"""
Unified command-line entry point.

All pipeline operations run through here — ingestion and API startup.
Single interface, consistent behaviour across all environments.

Does NOT: define business logic, load documents, or handle HTTP.

Usage:
    make api
    make ingest-resume
    make ingest-sanity
    make ingest-all
    uv run python -m src.main ingest --source resume sanity
    uv run python -m src.main ingest --source all
"""

import argparse
import asyncio

from src.core import bootstrap, logger


def main() -> None:
    """Parse CLI arguments and dispatch to the correct pipeline command.

    Commands:
        api     — start FastAPI server
        ingest  — ingest documents into the knowledge base

    Example:
        >>> # via Makefile
        >>> make api
        >>> make ingest-all
        >>> # via CLI
        >>> uv run python -m src.main ingest --source resume sanity
    """
    parser = argparse.ArgumentParser(
        description="Ask Chitrank — RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── api ────────────────────────────────────────────────────────────────
    subparsers.add_parser(
        "api",
        help="Start FastAPI server",
    )

    # ── ingest ─────────────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest documents into the knowledge base",
    )

    ingest_parser.add_argument(
        "--source",
        choices=["resume", "sanity", "linkedin"],
        nargs="+",
        default=["resume", "sanity", "linkedin"],
        help="Sources to ingest",
    )

    ingest_parser.add_argument(
        "--resume-url",
        default=None,
        help="Override resume URL from config",
    )

    args = parser.parse_args()
    bootstrap()

    # if args.command == "api":
    #     from src.api.app import main as run_api
    #     logger.info("Starting API server")
    #     run_api()

    if args.command == "ingest":
        asyncio.run(_run_ingest(args))

    else:
        parser.print_help()


async def _run_ingest(args: argparse.Namespace) -> None:
    """Run ingestion pipeline sequentially for specified sources.

    Expands 'all' to individual sources and runs each in order.
    Uses a single database session across all sources for consistency.

    Args:
        args: Parsed CLI arguments containing source list and resume_url.
    """
    from src.core.config import settings
    from src.db.connection import AsyncSessionLocal
    from src.ingestion.pipeline import ingest_resume, ingest_sanity

    resume_url = args.resume_url or settings.RESUME_URL

    # Expand "all" to individual sources in fixed order
    sources = args.source if isinstance(args.source, list) else [args.source]
    if "all" in sources:
        sources = ["resume", "sanity"]

    total_chunks = 0

    async with AsyncSessionLocal() as db:
        for source in sources:
            if source == "resume":
                logger.info(f"Ingesting resume from {resume_url}")
                count = await ingest_resume(resume_url, db)
                logger.success(f"Resume — {count} chunks stored")
                total_chunks += count

            elif source == "sanity":
                logger.info("Ingesting Sanity CMS")
                count = await ingest_sanity(db)
                logger.success(f"Sanity — {count} chunks stored")
                total_chunks += count

    logger.success(f"Ingestion complete — {total_chunks} total chunks stored")


if __name__ == "__main__":
    main()
