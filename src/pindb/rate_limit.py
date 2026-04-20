"""Per-IP rate limiter for sensitive auth endpoints.

Implemented as a FastAPI dependency backed directly by the `limits`
library. An earlier version used `slowapi.Limiter.limit` as a function
decorator, but its wrapper's `__globals__` is `slowapi.extension` —
which broke FastAPI's forward-ref resolution of `Annotated[str, Form()]`
under `from __future__ import annotations`, causing Form POSTs to land
as 422s. `dependencies=[Depends(rate_limit(...))]` leaves the route's
own signature untouched.

Keyed on `Request.client.host`. Behind a reverse proxy, configure it to
rewrite `X-Forwarded-For` and set ASGI `forwarded_allow_ips` so the real
client IP is visible here. Exceeding a limit raises `HTTPException(429)`
with a `Retry-After` header.
"""

from __future__ import annotations

import time

from fastapi import HTTPException, Request
from limits import RateLimitItem, parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)
_parsed_cache: dict[str, RateLimitItem] = {}


def _parse(limit_str: str) -> RateLimitItem:
    """Parse a limits-library limit string with process-wide memoization.

    Args:
        limit_str (str): String accepted by ``limits.parse`` (e.g. ``"5/minute"``).

    Returns:
        RateLimitItem: Parsed limit object reused for all calls with the same
            *limit_str*.
    """
    cached = _parsed_cache.get(limit_str)
    if cached is None:
        cached = parse(limit_str)
        _parsed_cache[limit_str] = cached
    return cached


def _client_ip(request: Request) -> str:
    """Best-effort client IP for rate-limit keying.

    Args:
        request (Request): Incoming request (uses ``request.client.host``).

    Returns:
        str: Remote host, or ``"unknown"`` when the client address is missing.
    """
    client = request.client
    return client.host if client else "unknown"


def rate_limit(limit_str: str):
    """Build a FastAPI dependency that enforces a per-IP, per-path limit.

    Args:
        limit_str (str): Limit specification for the ``limits`` library.

    Returns:
        Callable[[Request], None]: Dependency that raises ``HTTPException(429)``
            with ``Retry-After`` when the window is exceeded.
    """
    limit = _parse(limit_str)

    def dependency(request: Request) -> None:
        key = f"{request.url.path}:{_client_ip(request)}"
        if not _limiter.hit(limit, key):
            stats = _limiter.get_window_stats(limit, key)
            retry_after = max(1, int(stats.reset_time - time.time()))
            raise HTTPException(
                status_code=429,
                detail="Too many requests — slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def reset_rate_limits() -> None:
    """Clear all in-memory rate-limit counters.

    Intended for test setup and teardown so limits do not leak across cases.
    """
    _storage.reset()
