"""User account security: change password, link/unlink OAuth providers.

Routes:
  * ``GET  /user/me/security`` — page with password form + provider list
  * ``POST /user/me/password`` — change password (requires current when set)
  * ``POST /user/me/unlink/{provider}`` — detach a provider; refuses if it
    would leave the user with no way to log in.

The ``link`` action reuses ``/auth/{provider}?link=1`` which sets a
link-intent cookie consumed by the OAuth callback.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import delete, select

from pindb.auth import (
    SESSION_COOKIE,
    AuthenticatedUser,
    hash_password,
    verify_password,
)
from pindb.database import session_maker
from pindb.database.session import UserSession
from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider
from pindb.password_policy import PasswordPolicyError, validate_password
from pindb.rate_limit import rate_limit
from pindb.routes.auth._oauth import provider_enabled
from pindb.templates.auth.security import security_page

router = APIRouter(prefix="/user/me", tags=["user"])


def _enabled_providers() -> list[OAuthProvider]:
    return [p for p in OAuthProvider if provider_enabled(p)]


def _load_user_providers(user_id: int) -> list[UserAuthProvider]:
    with session_maker() as db:
        links = list(
            db.scalars(
                select(UserAuthProvider).where(UserAuthProvider.user_id == user_id)
            ).all()
        )
        for link in links:
            db.expunge(link)
        return links


@router.get("/security", response_model=None)
def get_security(
    request: Request,
    current_user: AuthenticatedUser,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    links = _load_user_providers(current_user.id)
    return HTMLResponse(
        content=str(
            security_page(
                request=request,
                current_user=current_user,
                linked_providers=links,
                enabled_providers=_enabled_providers(),
                error=error,
                success=success,
            )
        )
    )


@router.post(
    "/password",
    response_model=None,
    dependencies=[Depends(rate_limit("5/minute"))],
)
def post_change_password(
    request: Request,
    current_user: AuthenticatedUser,
    new_password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    current_password: Annotated[str | None, Form()] = None,
) -> Response:
    if new_password != confirm_password:
        return _render(request, current_user, error="New passwords do not match.")

    with session_maker() as db:
        user = db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        has_existing_password = user.hashed_password is not None
        username = user.username
        email = user.email

    if has_existing_password:
        if not current_password or not verify_password(
            plain=current_password,
            hashed=_fetch_hashed_password(current_user.id) or "",
        ):
            return _render(
                request, current_user, error="Current password is incorrect."
            )

    try:
        validate_password(new_password, username=username, email=email)
    except PasswordPolicyError as exc:
        return _render(
            request,
            current_user,
            error="Password does not meet the policy.",
            password_errors=exc.rules,
        )

    current_token = request.cookies.get(SESSION_COOKIE)
    with session_maker.begin() as db:
        user = db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.hashed_password = hash_password(new_password)
        # Revoke every sibling session. The caller's current session is
        # kept so they do not get logged out of the active device.
        stmt = delete(UserSession).where(UserSession.user_id == current_user.id)
        if current_token is not None:
            stmt = stmt.where(UserSession.token != current_token)
        db.execute(stmt)

    return RedirectResponse(
        url="/user/me/security?success=Password+updated", status_code=303
    )


def _fetch_hashed_password(user_id: int) -> str | None:
    with session_maker() as db:
        user = db.get(User, user_id)
        return user.hashed_password if user is not None else None


@router.post("/unlink/{provider}", response_model=None)
def post_unlink_provider(
    request: Request,
    current_user: AuthenticatedUser,
    provider: str,
) -> Response:
    try:
        provider_enum = OAuthProvider(provider)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown provider")

    with session_maker.begin() as db:
        user = db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        links = list(
            db.scalars(
                select(UserAuthProvider).where(UserAuthProvider.user_id == user.id)
            ).all()
        )
        target = next((link for link in links if link.provider is provider_enum), None)
        if target is None:
            return _render(
                request,
                current_user,
                error=f"No {provider_enum.value} account is linked.",
            )

        leaves_no_login = user.hashed_password is None and len(links) <= 1
        if leaves_no_login:
            return _render(
                request,
                current_user,
                error=(
                    "Can't unlink your only sign-in method. "
                    "Set a password first, or link another provider."
                ),
            )

        db.delete(target)

    return RedirectResponse(
        url=f"/user/me/security?success=Unlinked+{provider_enum.value}",
        status_code=303,
    )


def _render(
    request: Request,
    current_user: User,
    *,
    error: str | None = None,
    password_errors: list[str] | None = None,
) -> HTMLResponse:
    links = _load_user_providers(current_user.id)
    return HTMLResponse(
        content=str(
            security_page(
                request=request,
                current_user=current_user,
                linked_providers=links,
                enabled_providers=_enabled_providers(),
                error=error,
                password_errors=password_errors,
            )
        ),
        status_code=400,
    )
