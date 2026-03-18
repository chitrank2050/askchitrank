"""src/main.py

Unified command-line entry point.

All pipeline operations run through here — ingestion and API startup.
Single interface, consistent behaviour across all environments.

Does NOT: define business logic, load documents, or handle HTTP.

Usage:
    make ingest                                      — interactive menu
    uv run python -m src.main ingest --source resume
    uv run python -m src.main ingest --source sanity
    uv run python -m src.main ingest --source linkedin
    uv run python -m src.main ingest --source resume sanity linkedin
"""

import argparse
import asyncio

from src.core import bootstrap, logger


def main() -> None:
    """Parse CLI arguments and dispatch to the correct pipeline command.

    Commands:
        ingest  — ingest documents into the knowledge base from one
                  or more sources (resume, sanity, linkedin)

    Example:
        >>> # via Makefile interactive menu
        >>> make ingest
        >>> # via CLI directly
        >>> uv run python -m src.main ingest --source resume sanity
    """
    parser = argparse.ArgumentParser(
        description="Ask Chitrank — RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── ingest ─────────────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest documents into the knowledge base",
    )
    ingest_parser.add_argument(
        "--source",
        choices=["resume", "sanity", "linkedin"],
        nargs="+",  # accepts one or more values
        default=["resume", "sanity", "linkedin"],
        help=(
            "Sources to ingest. Pass one or more: "
            "--source resume sanity linkedin "
            "(default: all three)"
        ),
    )

    args = parser.parse_args()
    bootstrap()

    if args.command == "ingest":
        asyncio.run(_run_ingest(args))

    else:
        parser.print_help()


async def _run_ingest(args: argparse.Namespace) -> None:
    """Run ingestion pipeline sequentially for specified sources.

    Sources are always processed in a fixed order regardless of
    the order they were passed on the CLI — resume → sanity → linkedin.
    Uses a single database session across all sources for consistency.

    Args:
        args: Parsed CLI arguments containing:
            source: list of source names to ingest.
    """
    from src.db.connection import AsyncSessionLocal
    from src.ingestion.pipeline import ingest_linkedin, ingest_resume, ingest_sanity

    # Fixed processing order — predictable regardless of CLI argument order
    source_order = ["resume", "sanity", "linkedin"]
    sources = [s for s in source_order if s in args.source]

    total_chunks = 0

    async with AsyncSessionLocal() as db:
        for source in sources:
            if source == "resume":
                logger.info("Ingesting resume")
                count = await ingest_resume(db)
                logger.success(f"Resume — {count} chunks stored")
                total_chunks += count

            elif source == "sanity":
                logger.info("Ingesting Sanity CMS")
                count = await ingest_sanity(db)
                logger.success(f"Sanity — {count} chunks stored")
                total_chunks += count

            elif source == "linkedin":
                logger.info("Ingesting LinkedIn data")
                count = await ingest_linkedin(db)
                logger.success(f"LinkedIn — {count} chunks stored")
                total_chunks += count

    logger.success(f"Ingestion complete — {total_chunks} total chunks stored")


if __name__ == "__main__":
    main()
