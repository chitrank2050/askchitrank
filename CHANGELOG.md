# Changelog

All notable changes to Ask Chitrank.

## [0.3.0] - 2026-03-17

### Documentation

- Update project name references in CONTRIBUTING.md from ML-Notebook-Library to askchitrank.
- Add dedicated tech stack documentation and enhance project overview in the README and main documentation.

### Features

- Introduce a new database module with SQLAlchemy async connection management and ORM models for knowledge chunks, response cache, and conversations.
- Initialize Alembic for database migrations and define the initial schema for conversations, knowledge chunks, and response cache.
- Set up MkDocs and add initial documentation for development setup, architecture, and database.
- Add or update Makefile target to execute the `menu.py` script.
- Update Makefile to include new build targets and dependencies.

### Refactoring

- Adjust API lifespan management and event handling.

## [0.2.0] - 2026-03-17

### Documentation

- Add CONTRIBUTING.md and CODE_OF_CONDUCT.md to establish contribution guidelines and community standards.

### Features

- Establish core configuration, logging, and warning suppression utilities.
- Rename project from `folio-ai` to `askchitrank`.

### Refactoring

- Adjust API lifecycle management.

## [0.1.0] - 2026-03-17

### Features

- Initialize project with core structure, dependency management, development tools, and GitHub templates.


