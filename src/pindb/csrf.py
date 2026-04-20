"""Origin-header CSRF guard.

Unsafe methods (POST/PUT/PATCH/DELETE) must carry an ``Origin`` header
that matches ``CONFIGURATION.base_url``. Browsers always attach
``Origin`` on these methods for both XHR/fetch and form submissions, so
a missing header on an unsafe method is a strong signal that the request
did not originate from a browser on our site.

When ``Origin`` is absent we fall back to ``Referer`` — same-site check.
If neither header is present on an unsafe method, the request is
rejected with 403. GET/HEAD/OPTIONS are untouched.

The test-only OAuth provider (``allow_test_oauth_provider``) and the
``/auth/*/callback`` paths are exempt: OAuth redirects arrive without an
Origin that matches us, and the test endpoints are driven by the
integration suite.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import PlainTextResponse, Response

from pindb.config import CONFIGURATION

_SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/auth/google/callback",
    "/auth/discord/callback",
    "/auth/meta/callback",
    "/auth/_test-oauth/",
)


def _origin_host(value: str | None) -> tuple[str, str, int | None] | None:
    if not value:
        return None
    parts = urlsplit(value)
    if not parts.scheme or not parts.hostname:
        return None
    return (parts.scheme, parts.hostname, parts.port)


def _expected() -> tuple[str, str, int | None]:
    parts = urlsplit(CONFIGURATION.base_url)
    # base_url is validated as a non-empty string; hostname may be None for
    # malformed URLs — treat that as a configuration error at request time.
    return (parts.scheme, parts.hostname or "", parts.port)


def _matches(candidate: tuple[str, str, int | None]) -> bool:
    want = _expected()
    return candidate == want


async def csrf_origin_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not CONFIGURATION.csrf_enforce_origin:
        return await call_next(request)

    method = request.method.upper()
    if method in _SAFE_METHODS:
        return await call_next(request)

    path = request.url.path
    if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return await call_next(request)

    origin = _origin_host(request.headers.get("origin"))
    if origin is not None:
        if not _matches(origin):
            return PlainTextResponse("CSRF: bad Origin", status_code=403)
        return await call_next(request)

    referer = _origin_host(request.headers.get("referer"))
    if referer is not None:
        if not _matches(referer):
            return PlainTextResponse("CSRF: bad Referer", status_code=403)
        return await call_next(request)

    return PlainTextResponse(
        "CSRF: missing Origin/Referer on unsafe method", status_code=403
    )
