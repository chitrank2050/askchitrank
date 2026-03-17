#!/usr/bin/env python3
"""
Polished interactive checkbox menu.

Usage (via Makefile):
  uv run --with questionary scripts/menu.py [obliviate|git]
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import questionary
    from questionary import Choice
except ImportError:
    print("questionary not installed. Run: uv add questionary --dev")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent

# ── Polished style matching a modern dark-terminal look ──────────────────────
STYLE = questionary.Style(
    [
        ("qmark", "fg:#61dafb bold"),  # leading ? mark
        ("question", "fg:#ffffff bold"),  # prompt text
        ("answer", "fg:#61dafb bold"),  # confirmed answer
        ("pointer", "fg:#f0a500 bold"),  # ▶ cursor
        ("highlighted", "fg:#f0a500 bold"),  # row under cursor
        ("selected", "fg:#4ecca3"),  # ✔ ticked items
        ("separator", "fg:#555555 italic"),  # separator rows
        ("instruction", "fg:#555555"),  # keyboard hint line
    ]
)


# ── Helpers ──────────────────────────────────────────────────────────────────
def run_make(*targets: str) -> None:
    """Run one or more make targets, printing a warning if any fail."""
    for target in targets:
        result = subprocess.run(
            ["make", "--no-print-directory", target],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print(f"\n  ⚠️  make {target!r} exited with code {result.returncode}\n")


# ── Execution Orders — never change regardless of selection order ────────────
EXECUTION_ORDER_OBLIVIATE = [
    # Destructive first
    ("venv", lambda: run_make("_clean_venv")),
    ("cache", lambda: run_make("_clean_cache")),
    ("logs", lambda: run_make("_clean_logs")),
    # Setup second
    ("init", lambda: run_make("init")),
    ("install", lambda: run_make("install")),
    # Dev tools last
    ("lint", lambda: run_make("lint")),
    ("format", lambda: run_make("format")),
]


def _run_changelog_since() -> None:
    tag = questionary.text("Since tag (e.g. v0.1.0): ", style=STYLE).ask()
    if not tag:
        _nothing_selected()
        return
    print(f"📝 Changelog since {tag}...")
    subprocess.run(
        ["uv", "run", "git-cliff", f"{tag}..HEAD", "--strip", "all"], cwd=ROOT
    )


EXECUTION_ORDER_GIT = [
    ("_changelog", lambda: run_make("_changelog")),
    ("_changelog-preview", lambda: run_make("_changelog-preview")),
    ("_changelog-since", _run_changelog_since),
    ("_git-tag", lambda: run_make("_git-tag")),
    ("_git-release", lambda: run_make("_git-release")),
]


def _run_db_migration() -> None:
    name = questionary.text("Migration name: ", style=STYLE).ask()
    if not name:
        _nothing_selected()
        return
    print(f"🗄️  Creating migration: {name}...")
    result = subprocess.run(
        ["uv", "run", "alembic", "revision", "--autogenerate", "-m", name],
        cwd=ROOT,
        env={**os.environ, "APP_ENV": "dev"},
    )
    if result.returncode == 0:
        print("✅ Migration created.")
    else:
        print(f"⚠️  Migration creation failed with code {result.returncode}.")


def execute_choices(choices: list[str], order_list: list[tuple[str, Any]]) -> None:
    """Execute selected actions in fixed dependency order, never user-selection order."""
    for key, fn in order_list:
        if key in choices:
            fn()


def _nothing_selected() -> None:
    print("\n  Nothing selected — no action taken.\n")


# ── Mode: obliviate ──────────────────────────────────────────────────────────
def mode_obliviate() -> None:
    choices = questionary.checkbox(
        "🧹 Obliviate — select what to obliterate",
        choices=[
            Choice(
                "Cache files    (__pycache__, .pyc, dist, .ruff_cache…)", value="cache"
            ),
            Choice("Saved models   (models/)", value="models"),
            Choice("MLflow data    (mlruns.db, mlruns/)", value="mlflow_clean"),
            Choice("Logs           (logs/)", value="logs"),
            Choice("Virtual env    (.venv)", value="venv"),
        ],
        style=STYLE,
    ).ask()

    if not choices:
        _nothing_selected()
        return

    execute_choices(choices, EXECUTION_ORDER_OBLIVIATE)


# ── Mode: git ────────────────────────────────────────────────────────────────
def mode_git() -> None:
    choices = questionary.checkbox(
        "🐙 Git — select actions",
        choices=[
            Choice("Generate CHANGELOG.md", value="_changelog"),
            Choice("Preview unreleased changes", value="_changelog-preview"),
            Choice("Preview changes since custom tag", value="_changelog-since"),
            Choice("Tag version from pyproject.toml", value="_git-tag"),
            Choice("Release (Tag + Changelog + GitHub release)", value="_git-release"),
        ],
        style=STYLE,
    ).ask()

    if not choices:
        _nothing_selected()
        return

    execute_choices(choices, EXECUTION_ORDER_GIT)


# ── Entry point ──────────────────────────────────────────────────────────────
MODES = {
    "obliviate": mode_obliviate,
    "git": mode_git,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in MODES:
        print(f"Usage: {sys.argv[0]} [{format('|'.join(MODES.keys()))}]")
        sys.exit(1)

    mode = sys.argv[1]

    try:
        MODES[mode]()
    except KeyboardInterrupt:
        print("\n\n  ✖ Cancelled — no action taken.\n")
        sys.exit(0)
