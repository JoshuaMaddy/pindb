"""HTMX toast payloads and helpers for PostgreSQL unique violations.

``unique_constraint_response`` returns a small HTML fragment that Alpine uses
to show a toast for HTMX requests, or a plain conflict response otherwise.

Success paths use the ``HX-Trigger`` header with a ``pindbToast`` payload; the
client shows a Notyf toast before following ``HX-Redirect``.
"""

from __future__ import annotations

import json

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from htpy import div
from sqlalchemy.exc import IntegrityError


def is_unique_violation(exc: IntegrityError) -> bool:
    """Return whether *exc* is a PostgreSQL unique constraint violation (23505).

    Args:
        exc (IntegrityError): Exception raised from a failed flush/commit.

    Returns:
        bool: ``True`` when the wrapped DB-API error indicates SQLSTATE 23505 or
            a ``UniqueViolation`` driver type.
    """
    error_origin = exc.orig
    if error_origin is None:
        return False
    if getattr(error_origin, "pgcode", None) == "23505":
        return True
    if getattr(error_origin, "sqlstate", None) == "23505":
        return True
    if type(error_origin).__name__ == "UniqueViolation":
        return True
    return False


def _toast_signal_html(*, message: str, toast_type: str) -> str:
    """Build a hidden marker element the client reads for toast text and style.

    Args:
        message (str): User-visible message.
        toast_type (str): Client-side category (e.g. ``"error"``).

    Returns:
        str: HTML string for the toast signal element.
    """
    return str(
        div(
            id="pindb-toast-signal",
            data_pindb_message=message,
            data_pindb_type=toast_type,
        )
    )


def hx_trigger_toast_json(*, message: str, toast_type: str = "success") -> str:
    """Return JSON for the ``HX-Trigger`` response header (``pindbToast`` event)."""
    return json.dumps(obj={"pindbToast": {"message": message, "type": toast_type}})


def hx_redirect_with_toast_headers(
    *,
    redirect_url: str,
    message: str,
    toast_type: str = "success",
) -> dict[str, str]:
    """Headers for an HTMX response: redirect plus a toast signal."""
    return {
        "HX-Redirect": redirect_url,
        "HX-Trigger": hx_trigger_toast_json(message=message, toast_type=toast_type),
    }


def htmx_error_toast(
    *,
    message: str,
    toast_type: str = "error",
) -> HTMLResponse:
    """Empty-body 200 response that fires ``pindbToast`` on the client."""
    return HTMLResponse(
        content="",
        headers={
            "HX-Trigger": hx_trigger_toast_json(message=message, toast_type=toast_type)
        },
    )


def redirect_or_htmx_toast(
    request: Request,
    *,
    redirect_url: str,
    message: str,
    toast_type: str = "success",
) -> HTMLResponse | RedirectResponse:
    """303 redirect for full-page posts; HTMX gets ``HX-Redirect`` + ``HX-Trigger``."""
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            headers=hx_redirect_with_toast_headers(
                redirect_url=redirect_url,
                message=message,
                toast_type=toast_type,
            )
        )
    return RedirectResponse(url=redirect_url, status_code=303)


def unique_constraint_response(
    *,
    request: Request,
    message: str = "That name or alias is already in use.",
    toast_type: str = "error",
) -> HTMLResponse:
    """Respond with a toast fragment for HTMX, or plain text for full-page posts.

    Args:
        request (Request): Current request (checks ``HX-Request``).
        message (str): Error text shown to the user.
        toast_type (str): Passed to the toast signal as ``data-pindb-type``.

    Returns:
        HTMLResponse: For HTMX, a ``200`` HTML fragment carrying the toast
            signal; otherwise ``409`` ``text/plain`` with *message*.
    """
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=str(_toast_signal_html(message=message, toast_type=toast_type))
        )
    return HTMLResponse(content=message, media_type="text/plain", status_code=409)
