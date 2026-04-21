"""Response-header middleware for baseline web security.

Headers set:

- ``Strict-Transport-Security`` — 2 years, includeSubDomains, preload.
  Only emitted when ``session_cookie_secure`` is enabled, so local
  plain-HTTP dev does not latch browsers onto HTTPS for ``localhost``.
- ``X-Content-Type-Options: nosniff`` — stops MIME sniffing (images in
  particular were served with a bare ``image`` type before).
- ``X-Frame-Options: DENY`` — no third-party framing.
- ``Referrer-Policy: strict-origin-when-cross-origin``.
- ``Content-Security-Policy`` — report-only for now because inline
  ``<script>`` blocks are used for Alpine/HTMX glue. The policy still
  constrains ``object-src`` and ``base-uri``; tighten to enforce mode
  once the inline scripts migrate to external files with nonces.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response

from pindb.config import CONFIGURATION

_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net "
    "https://static.cloudflareinsights.com; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
    "font-src 'self' data: https://cdn.jsdelivr.net; "
    "connect-src 'self' https://cloudflareinsights.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "form-action 'self'"
)


async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach baseline security headers to every response.

    Args:
        request (Request): Incoming ASGI request.
        call_next (Callable): Next handler in the stack.

    Returns:
        Response: The downstream response with headers merged in (see module
            docstring for which headers are set and when HSTS applies).

    Note:
        Uses ``setdefault`` so route handlers may override values when needed.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy-Report-Only", _CSP)
    if CONFIGURATION.session_cookie_secure:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
    return response
