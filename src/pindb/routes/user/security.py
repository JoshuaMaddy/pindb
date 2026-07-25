"""User account security: change password.

Routes:
  * ``GET  /user/me/security`` — page with the password form
  * ``POST  /user/me/password`` — change password (requires current when set)

A password is the only credential PinDB accepts; provider linking went away
with OAuth.
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
from pindb.database import async_session_maker
from pindb.database.session import UserSession
from pindb.database.user import User
from pindb.password_policy import PasswordPolicyError, validate_password
from pindb.rate_limit import rate_limit
from pindb.templates.auth.security import security_page

router = APIRouter(prefix="/user/me", tags=["user"])


@router.get("/security", response_model=None)
async def get_security(
    request: Request,
    current_user: AuthenticatedUser,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            security_page(
                request=request,
                current_user=current_user,
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
async def post_change_password(
    request: Request,
    current_user: AuthenticatedUser,
    new_password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    current_password: Annotated[str | None, Form()] = None,
) -> Response:
    if new_password != confirm_password:
        return await _render(request, current_user, error="New passwords do not match.")

    async with async_session_maker() as db:
        user = await db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        has_existing_password = user.hashed_password is not None
        username = user.username
        email = user.email

    if has_existing_password:
        if not current_password or not verify_password(
            plain=current_password,
            hashed=(await _fetch_hashed_password(current_user.id)) or "",
        ):
            return await _render(
                request, current_user, error="Current password is incorrect."
            )

    try:
        validate_password(new_password, username=username, email=email)
    except PasswordPolicyError as exc:
        return await _render(
            request,
            current_user,
            error="Password does not meet the policy.",
            password_errors=exc.rules,
        )

    current_token = request.cookies.get(SESSION_COOKIE)
    async with async_session_maker.begin() as db:
        user = await db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.hashed_password = hash_password(new_password)
        # Revoke every sibling session. The caller's current session is
        # kept so they do not get logged out of the active device.
        stmt = delete(UserSession).where(UserSession.user_id == current_user.id)
        if current_token is not None:
            stmt = stmt.where(UserSession.token != current_token)
        await db.execute(stmt)

    return RedirectResponse(
        url="/user/me/security?success=Password+updated", status_code=303
    )


async def _fetch_hashed_password(user_id: int) -> str | None:
    async with async_session_maker() as db:
        user = await db.get(User, user_id)
        return user.hashed_password if user is not None else None


async def _render(
    request: Request,
    current_user: User,
    *,
    error: str | None = None,
    password_errors: list[str] | None = None,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            security_page(
                request=request,
                current_user=current_user,
                error=error,
                password_errors=password_errors,
            )
        ),
        status_code=400,
    )
