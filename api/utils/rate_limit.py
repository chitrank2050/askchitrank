"""
Rate limiter instance.

Defined in its own module to avoid circular imports between
app.py and route files. Both import from here.

Responsibility: provide the rate limiter singleton. Nothing else.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Single limiter instance — imported by app.py and all route files
limiter = Limiter(key_func=get_remote_address)
