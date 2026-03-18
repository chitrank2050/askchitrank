# ─────────────────────────────────────────────────────────────────────────────
# Makefile for Ask Chitrank
# ─────────────────────────────────────────────────────────────────────────────
VENV := .venv
UV   := uv
PYTHON_VERSION := $(shell if [ -f .python-version ]; then cat .python-version; else echo "3.12"; fi)

.DEFAULT_GOAL := help
.PHONY: help init install install-prod \
        db _db-migrate _db-migration _db-rollback \
        lint format tree python-version obliviate \
        git _changelog _changelog-preview _changelog-since _git-tag _git-release \
        docs _docs _docs-build _docs-deploy \
				ingest

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Ask Chitrank"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Setup:"
	@echo "  make init           - Create virtual environment"
	@echo "  make install        - Install all dependencies"
	@echo "  make install-prod   - Install production dependencies only"
	@echo ""
	@echo "API:"
	@echo "  make api            - Start FastAPI server"
	@echo ""
	@echo "Interactive Menus:"
	@echo "  make git            - Changelog & release menu"
	@echo "  make obliviate      - Clean menu"
	@echo "  make docs           - Documentation menu"
	@echo "  make db             - Manage Alembic database migrations"
	@echo "  make ingest         - Ingest data into the database"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Ruff check"
	@echo "  make format         - Ruff format"
	@echo ""
	@echo "Maintenance:"
	@echo "  make tree           - Print project structure"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
init:
	@echo "🚀 Creating virtual environment with Python $(PYTHON_VERSION)..."
	@if [ -d "$(VENV)" ]; then \
		echo "⚠️  Virtual environment already exists."; \
		echo "💡 Run 'make obliviate' first to remove it."; \
		exit 1; \
	fi
	$(UV) venv --python $(PYTHON_VERSION)
	@echo "✅ Done. Run 'make install' next."

install:
	@echo "📥 Installing dependencies..."
	$(UV) sync --all-groups
	@echo "✅ Done."

install-prod:
	@echo "📥 Installing production dependencies..."
	@$(UV) sync --no-dev
	@echo "✅ Done."

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────
lint:
	@echo "🔍 Checking code quality..."
	$(UV) run --no-sync ruff check . --fix

format:
	@echo "✨ Formatting code..."
	$(UV) run --no-sync ruff format .

# ─────────────────────────────────────────────────────────────────────────────
# Maintenance
# ─────────────────────────────────────────────────────────────────────────────
tree:
	@echo "🌳 Project Structure:"
	@find . \
		-not -path './.venv/*' \
		-not -path './.git/*' \
		-not -path '*/__pycache__/*' \
		-not -path './.ruff_cache/*' \
		| sort | sed 's/[^/]*\//  /g'

_clean_cache:
	@echo "🧹 Removing cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf site/ dist/ .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov 2>/dev/null || true
	@echo "✅ Cache cleaned"

_clean_logs:
	@echo "🧹 Removing log files..."
	@rm -rf logs/
	@echo "✅ Log files removed"

_clean_venv:
	@echo "🗑️  Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "✅ Virtual environment removed"

obliviate:
	$(UV) run --with questionary scripts/menu.py obliviate

python-version:
	@echo "📌 Python version: $(PYTHON_VERSION)"
	@$(UV) python list 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────
api:
	@echo "🚀 Starting API server..."
	@$(UV) run python -m src.main api


# ─────────────────────────────────────────────────────────────────────────────
# Git
# ─────────────────────────────────────────────────────────────────────────────
git:
	$(UV) run --with questionary scripts/menu.py git

_changelog:
	@echo "📝 Generating changelog..."
	@$(UV) run git-cliff --output CHANGELOG.md
	@git add CHANGELOG.md
	@git diff --cached --quiet || git commit --no-verify -m "docs: update changelog"
	@git push
	@echo "✅ Changelog updated."

_changelog-preview:
	@echo "📝 Preview unreleased changes..."
	@$(UV) run git-cliff --unreleased --strip all

_changelog-since:
	@read -p "Since tag (e.g. v0.1.0): " tag; \
	echo "📝 Changelog since $$tag..."; \
	$(UV) run git-cliff "$$tag"..HEAD --strip all

_git-tag:
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | tr -d '"' | tr -d ' ' | cut -d'=' -f2); \
	echo "🏷️  Tagging v$$VERSION..."; \
	git tag "v$$VERSION" -m "Release v$$VERSION"; \
	git push --tags; \
	echo "✅ Tagged v$$VERSION"

_git-release:
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | tr -d '"' | tr -d ' ' | cut -d'=' -f2); \
	echo "📦 Releasing v$$VERSION..."; \
	$(UV) run git-cliff --output CHANGELOG.md; \
	git add CHANGELOG.md; \
	git diff --cached --quiet || git commit --no-verify -m "docs: update changelog for v$$VERSION"; \
	git push; \
	NOTES=$$($(UV) run git-cliff --latest --strip all 2>/dev/null); \
	gh release edit "v$$VERSION" \
		--title "v$$VERSION" \
		--notes "$$NOTES" 2>/dev/null || \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--notes "$$NOTES"; \
	echo "✅ Released v$$VERSION"; \
	echo "   https://github.com/chitrank2050/askchitrank/releases/tag/v$$VERSION"

# ─────────────────────────────────────────────────────────────────────────────
# Docs
# ─────────────────────────────────────────────────────────────────────────────
docs:
	$(UV) run --with questionary scripts/menu.py docs

_docs:
	@echo "📚 Starting MkDocs server..."
	@cp CHANGELOG.md docs/changelog.md
	@$(UV) run mkdocs serve

_docs-build:
	@echo "📚 Building docs site..."
	@cp CHANGELOG.md docs/changelog.md
	@$(UV) run mkdocs build
	@echo "✅ Docs built in site/"

_docs-deploy:
	@echo "📚 Deploying to GitHub Pages..."
	@rm -rf docs/changelog.md
	@cp CHANGELOG.md docs/changelog.md
	@$(UV) run mkdocs gh-deploy --force
	@echo "✅ Deployed to https://chitrank2050.github.io/askchitrank"

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────
db:
	$(UV) run --with questionary scripts/menu.py db

_db-migrate:
	@echo "🗄️  Running database migrations..."
	@$(UV) run alembic upgrade head
	@echo "✅ Migrations complete."

_db-migration:
	@read -p "Migration name: " name; \
	echo "🗄️  Creating migration: $$name..."; \
	$(UV) run alembic revision --autogenerate -m "$$name"; \
	echo "✅ Migration created."

_db-rollback:
	@echo "🗄️  Rolling back last migration..."
	@$(UV) run alembic downgrade -1
	@echo "✅ Rolled back."

# ─────────────────────────────────────────────────────────────────────────────
# Ingestion — interactive menu selects source
# ─────────────────────────────────────────────────────────────────────────────
ingest:
	$(UV) run --with questionary scripts/menu.py ingest

_ingest-resume:
	@echo "📄 Ingesting resume..."
	@$(UV) run python -m src.main ingest --source resume

_ingest-sanity:
	@echo "🌐 Ingesting Sanity CMS..."
	@$(UV) run python -m src.main ingest --source sanity

_ingest-linkedin:
	@echo "💼 Ingesting LinkedIn PDF..."
	@$(UV) run python -m src.main ingest --source linkedin