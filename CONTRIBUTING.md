# Contributing to Ask Chitrank

Thank you for considering contributing. If you've noticed a bug or have a feature request, [open an issue](https://github.com/chitrank2050/askchitrank/issues/new) before starting to code.

---

## Getting Started

### Fork and create a branch

[Fork the repo](https://github.com/chitrank2050/askchitrank/fork) and create a branch with a descriptive name:

```bash
git checkout -b 42-fix-cache-invalidation
```

### Set up the project

Follow this doc for setting up the project: [Setup & Installation](https://chitrank2050.github.io/askchitrank/development/setup/)

### Make your changes

Follow the existing code style — Google-style docstrings, type hints on all functions, ruff for formatting.

```bash
make lint
make format
```

### Open a Pull Request

Push your branch and open a PR against `main`. Include:
- What the change does
- Why it's needed
- Any relevant issue numbers

---

## Reporting Security Issues

Do NOT open a public issue for security vulnerabilities. Please follow the instructions in [SECURITY.md](SECURITY.md).

---

## Commit Messages

Follow conventional commits:

```
feat: add LinkedIn ingestion pipeline
fix: resolve cache invalidation on webhook
chore: update dependencies
docs: add ingestion pipeline documentation
```