"""HTMX-friendly toast payloads and PostgreSQL integrity helpers."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from fastapi import Request
from fastapi.responses import HTMLResponse
from htpy import div


def is_unique_violation(exc: IntegrityError) -> bool:
    """True when ``exc`` is a PostgreSQL unique constraint violation (23505)."""
    orig = exc.orig
    if orig is None:
        return False
    if getattr(orig, "pgcode", None) == "23505":
        return True
    if getattr(orig, "sqlstate", None) == "23505":
        return True
    if type(orig).__name__ == "UniqueViolation":
        return True
    return False


def _toast_signal_html(*, message: str, toast_type: str) -> str:
    return str(
        div(
            id="pindb-toast-signal",
            data_pindb_message=message,
            data_pindb_type=toast_type,
        )
    )


def unique_constraint_response(
    *,
    request: Request,
    message: str = "That name or alias is already in use.",
    toast_type: str = "error",
) -> HTMLResponse:
    """Toast fragment for HTMX; plain conflict response otherwise."""
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content=_toast_signal_html(message=message, toast_type=toast_type)
        )
    return HTMLResponse(content=message, media_type="text/plain", status_code=409)
