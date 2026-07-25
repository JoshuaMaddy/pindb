"""Default-deny authentication gate.

PinDB is a private community: every path is members-only unless it appears in
the allowlist below. The gate is middleware rather than per-route
``AuthenticatedUser`` dependencies for three reasons:

1. A route added later is private by default. With dependencies, one forgotten
   annotation silently publishes catalog data.
2. Dependencies never run for ``app.mount()``-ed apps, so ``/static`` and
   ``/templates-js`` could not be reasoned about at all.
3. It runs before routing, so 404/405/validation responses stop being an
   existence oracle for anonymous visitors.

Ordering matters (see ``pindb.__init__``): this sits *inside*
``attach_user_middleware`` so it reads the already-resolved
``request.state.user`` rather than hitting the database a second time, and
*inside* the CSRF and security-header middlewares so rejected requests still
carry the baseline headers and a cross-origin POST still reads as CSRF rather
than leaking whether authentication would have let it through.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response

LOGIN_PATH = "/auth/login"

# Exact paths reachable without a session.
#
# ``/auth/logout`` is here so a stale or half-valid cookie can always be
# cleared. ``/`` deliberately is NOT: the homepage renders real pin images.
# Legal and docs pages are not public either — login is the only page an
# anonymous visitor sees.
PUBLIC_EXACT: frozenset[str] = frozenset(
    {
        "/healthz",
        LOGIN_PATH,
        "/auth/logout",
        "/robots.txt",
        "/favicon.ico",
    }
)

# Mounted asset apps. Safe only because the editor docs markdown was moved out
# of ``static/`` to ``pindb/docs_content/`` — anything under a mount is served
# raw, without routing and without this gate having a route to reason about.
PUBLIC_PREFIXES: tuple[str, ...] = ("/static/", "/templates-js/")


def is_public_path(path: str) -> bool:
    """Return whether *path* may be served to an anonymous visitor.

    Args:
        path (str): Request path, without query string.

    Returns:
        bool: ``True`` when *path* is allowlisted.
    """
    if path in PUBLIC_EXACT:
        return True
    return path.startswith(PUBLIC_PREFIXES)


def safe_next_target(raw: str | None) -> str | None:
    """Validate a post-login redirect target from user input.

    Only site-relative paths are accepted. A value starting with ``//`` (or
    ``/\\``) is rejected because browsers read it as a protocol-relative URL to
    another host, which would turn the login form into an open redirect.

    Args:
        raw (str | None): Candidate value from the ``next`` query or form field.

    Returns:
        str | None: The target when it is a safe relative path, else ``None``.
    """
    if not raw or not raw.startswith("/"):
        return None
    if raw.startswith(("//", "/\\")):
        return None
    return raw


def _login_redirect_url(request: Request) -> str:
    """Build the login URL carrying the requested path as ``next``."""
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    if safe_next_target(target) is None:
        return LOGIN_PATH
    return f"{LOGIN_PATH}?next={quote(target, safe='')}"


async def require_login_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Reject anonymous requests to any path outside the public allowlist.

    Three response shapes, because three kinds of caller reach this:

    - HTMX requests get ``401`` plus ``HX-Redirect`` so an expired session
      navigates to the login page instead of firing an error toast.
    - Browser navigations (``Accept: text/html`` on GET) get a ``303`` to the
      login page with a ``next`` parameter.
    - Everything else gets a plain ``401``. This is what keeps API-style
      callers and the integration suite's ``anon_client`` honest — ``TestClient``
      sends ``Accept: */*`` and expects a status code, not a redirect.

    Args:
        request (Request): Incoming ASGI request.
        call_next (Callable): Next middleware or route handler.

    Returns:
        Response: Downstream response, or a rejection as described above.
    """
    if getattr(request.state, "user", None) is not None:
        return await call_next(request)

    if is_public_path(request.url.path):
        return await call_next(request)

    if request.headers.get("HX-Request"):
        return Response(status_code=401, headers={"HX-Redirect": LOGIN_PATH})

    accept = request.headers.get("accept", "")
    if request.method in ("GET", "HEAD") and "text/html" in accept:
        return RedirectResponse(url=_login_redirect_url(request), status_code=303)

    return PlainTextResponse("Authentication required", status_code=401)
