# Changelog

All notable changes to Ask Chitrank.

## [Unreleased]

### Documentation

- Update project version to 0.6.1 and add live API link

## [0.6.0] - 2026-03-18

### Documentation

- Add descriptive comments to Makefile targets and commands.

### Features

- Implement unified API token authentication and custom error handling across API endpoints, and refine the ingestion pipeline.

### Maintenance

- Reorder MkDocs navigation entries.

### Refactoring

- Restructure Bruno API collection into granular tests and enhance API documentation with auth, validation, and error details.

## [0.5.0] - 2026-03-18

### Documentation

- Add API and chat layer overviews, update project progress, and rename Sanity webhook secret configuration.

### Features

- Implement source-diverse retrieval by limiting results per source and refine ingestion to categorize testimonials separately.
- Implement RAG chat functionality with Groq LLM integration and streaming capabilities.
- Introduce a new FastAPI server with rate limiting, accessible via a dedicated CLI command.
- Establish core API with v1 endpoints for health, streaming chat, and Sanity content ingestion, including their respective schemas and routing.
- Add `stream` option to chat requests, allowing clients to choose between SSE streaming and a single JSON response.
- Introduce Bruno API collection with local environment, chat, health, and ingest endpoints.
- Implement API security headers, update documentation with new concepts and Sanity webhook setup, and add cache invalidation to the ingestion pipeline.

### Maintenance

- Update project name from Folio AI to Ask Chitrank in changelog and config.
- Update GROQ_MODEL to llama-3.3-70b-versatile in configuration and documentation.

## [0.4.5] - 2026-03-18

### Bug Fixes

- Corrected author's last name in mkdocs.yml.

## [0.4.4] - 2026-03-18

### Bug Fixes

- Dead retrieval docs

## [0.4.2] - 2026-03-18

### Documentation

- Mark Phase 3 of the retrieval layer as complete in the project roadmap.

### Features

- Implement semantic response caching and knowledge base similarity search.

## [0.4.1] - 2026-03-18

### Refactoring

- Use `Path.open` and remove unused website URL parsing logic in the LinkedIn loader.

## [0.4.0] - 2026-03-18

### Documentation

- CHANGELOG project name references
- Expand tech stack documentation with new sections and tools, and refine database schema descriptions.

### Features

- Implement a document ingestion pipeline to load, chunk, and embed data from PDF and Sanity CMS.
- Implement URL-based resume ingestion and Sanity API token authentication, with improved logging and documentation.
- Update build configuration and menu script for improved functionality.
- Add 'linkedin' as an ingestion source, remove 'all' option, and update default ingestion sources.
- Add LinkedIn profile data ingestion from CSV exports.
- Add functionality to load and extract text from local PDF files and update `greenlet` dependency.
- Revamp LinkedIn data ingestion to use Profile.csv and filter Recommendations_Received.csv, replacing previous CSVs and adding profile formatting.
- Implement section-aware chunking for resumes with fallback to word-count chunking and update data path retrieval.
- Update resume ingestion to use local PDF, switch LinkedIn ingestion to CSVs, and refactor PDF text extraction
- Expand knowledge base to include LinkedIn, update project roadmap, and refine documentation.
- Add ingestion and retrieval overview documentation and update mkdocs navigation.

### Maintenance

- Bump project version to 0.4.0.

### Refactoring

- Use `pathlib.Path.open` in `linkedin_loader` and add `strict=False` to `zip` in `pipeline`.

## [0.3.0] - 2026-03-17

### Documentation

- Update project name references in CONTRIBUTING.md from ML-Notebook-Library to askchitrank.
- Add dedicated tech stack documentation and enhance project overview in the README and main documentation.

### Features

- Introduce a new database module with SQLAlchemy async connection management and ORM models for knowledge chunks, response cache, and conversations.
- Initialize Alembic for database migrations and define the initial schema for conversations, knowledge chunks, and response cache.up
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
- Rename project to `folio-ai` to `askchitrank` and

### Refactoring

- Adjust API lifecycle management.

## [0.1.0] - 2026-03-17

### Features

- Initialize project with core structure, dependency management, development tools, and GitHub templates.


