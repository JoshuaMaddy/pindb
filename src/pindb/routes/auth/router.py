"""Authentication routes: login and logout.

PinDB is a private community. There is no self-service signup and no OAuth —
accounts are created by an admin at ``/admin/users``, and a password is the
only credential. ``/auth/login`` and ``/auth/logout`` are the only paths here
on the public allowlist (see ``pindb.require_login``).

There is no password-reset flow, by design: with no outbound email, recovery
means an admin setting a new password.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import (
    SESSION_TTL,
    clear_session_cookie,
    set_session_cookie,
    verify_dummy_password,
    verify_password,
)
from pindb.database import UserSession, async_session_maker
from pindb.database.user import User
from pindb.rate_limit import enforce_limit, rate_limit
from pindb.require_login import LOGIN_PATH, safe_next_target
from pindb.templates.auth.login import login_page

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


async def _create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    async with async_session_maker.begin() as db:
        db.add(
            UserSession(
                token=token,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                + SESSION_TTL,
            )
        )
    return token


# ---------------------------------------------------------------------------
# Password login / logout
# ---------------------------------------------------------------------------


def _render_login(
    request: Request,
    *,
    error: str | None = None,
    next_target: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            login_page(
                request=request,
                error=error,
                next_target=next_target,
            )
        ),
        status_code=status_code,
    )


@router.get("/login", response_model=None)
async def get_login(
    request: Request,
    error: str | None = None,
    next: str | None = None,
) -> HTMLResponse:
    return _render_login(request, error=error, next_target=safe_next_target(next))


@router.post(
    "/login",
    response_model=None,
    dependencies=[Depends(rate_limit("10/minute"))],
)
async def post_login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str | None, Form()] = None,
) -> HTMLResponse | RedirectResponse:
    # Validated, not trusted: an unchecked value here would make the login form
    # an open redirect for anyone who can get a member to click a crafted link.
    next_target = safe_next_target(next)

    # Per-IP limiting alone does not stop a spray across many addresses at one
    # account, so the account itself gets a budget too.
    enforce_limit(f"login-username:{username.strip().lower()}", "10/minute")

    async with async_session_maker() as db:
        user: User | None = (
            await db.scalars(select(User).where(User.username == username))
        ).first()

    if user is None or user.hashed_password is None:
        # Burn an Argon2 verify against a dummy hash so missing users cost
        # roughly the same time as bad passwords — closes the timing oracle.
        # A user with no password hash can no longer log in at all: those rows
        # are OAuth-era leftovers and need an admin-set password.
        verify_dummy_password(password)
        return _render_login(
            request,
            error="Invalid username or password.",
            next_target=next_target,
            status_code=401,
        )

    if not verify_password(plain=password, hashed=user.hashed_password):
        return _render_login(
            request,
            error="Invalid username or password.",
            next_target=next_target,
            status_code=401,
        )

    token: str = await _create_session(user.id)
    response = RedirectResponse(url=next_target or "/", status_code=303)
    set_session_cookie(response, token)
    return response


@router.post("/logout", response_model=None)
async def post_logout(request: Request) -> RedirectResponse:
    token: str | None = request.cookies.get("session")
    if token:
        async with async_session_maker.begin() as db:
            user_session: UserSession | None = await db.get(UserSession, token)
            if user_session:
                await db.delete(user_session)

    response = RedirectResponse(url=LOGIN_PATH, status_code=303)
    clear_session_cookie(response)
    return response
