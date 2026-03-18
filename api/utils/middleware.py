"""Custom middleware for the FastAPI application."""

from uuid import uuid4

from fastapi import Request


async def add_security_headers(request: Request, call_next):
    """Add standard security headers to every response."""
    response = await call_next(request)
    # Prevent browsers from MIME-sniffing a response away from the declared content-type
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking by not allowing this site to be embedded in an iframe
    response.headers["X-Frame-Options"] = "DENY"
    # Enable reflective XSS protection in older browsers
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Enforce HTTPS (HSTS) if not in debug mode
    # Assuming we set this in PRODUCTION, but for safety check settings later
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Content Security Policy - very restrictive by default for an API
    # Only allow scripts from 'self' and no inline scripts/styles (if possible)
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "base-uri 'self'; "
        "font-src 'self' https: data:; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: https:; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline'; "  # unsafe-inline for Swagger if needed
        "style-src 'self' 'unsafe-inline' https:; "  # unsafe-inline for Swagger/Redoc
        "upgrade-insecure-requests;"
    )
    return response


async def add_request_id(request: Request, call_next):
    """Add unique request ID to every request for tracing."""
    request_id = str(uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
