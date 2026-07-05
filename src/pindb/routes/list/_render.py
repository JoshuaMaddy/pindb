"""Shared HTMX dispatch for entity-list routes.

Every list route renders the section fragment for HTMX requests and the full
page otherwise, passing the same ``request`` plus keyword arguments to both.
"""

from collections.abc import Callable

from fastapi import Request
from htpy import Element
from htpy.starlette import HtpyResponse


def list_response(
    request: Request,
    *,
    full: Callable[..., Element],
    section: Callable[..., Element],
    **kwargs: object,
) -> HtpyResponse:
    """Render ``section`` for HTMX requests, otherwise ``full``."""
    template = section if request.headers.get("HX-Request") else full
    return HtpyResponse(template(request=request, **kwargs))
