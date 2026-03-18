"""
FastAPI application package.

Exports the application factory and singleton for use
in tests and deployment.

Typical usage:
    from src.api.app import app, create_app
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
