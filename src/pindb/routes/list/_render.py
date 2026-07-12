"""Shared HTMX dispatch for entity-list routes.

Every list route renders the section fragment for HTMX requests and the full
page otherwise, passing the same ``request`` plus keyword arguments to both.
"""

from collections.abc import Callable

from fastapi import Request
from fastapi.responses import HTMLResponse
from htpy import Element


def list_response(
    request: Request,
    *,
    full: Callable[..., Element],
    section: Callable[..., Element],
    **kwargs: object,
) -> HTMLResponse:
    """Render ``section`` for HTMX requests, otherwise ``full``.

    Renders to a string here rather than handing the element tree to
    ``HtpyResponse``. That response streams the tree node by node, and a list page
    is ~100 entity cards — tens of thousands of async chunk yields pumped through
    anyio memory streams and the middleware stack, which measured ~4x the cost of
    just building the string. It also renders *lazily*, after the route's session
    has closed, so any relationship the template touched would raise
    ``DetachedInstanceError``; ``str()`` here happens while the session is open.
    The ``get/*`` detail pages already render this way.
    """
    template = section if request.headers.get("HX-Request") else full
    return HTMLResponse(content=str(template(request=request, **kwargs)))
