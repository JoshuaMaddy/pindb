"""
FastAPI routes: `routes/admin/users.py`.
"""

from typing import Annotated, Sequence
from urllib.parse import quote

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import AdminUser, hash_password
from pindb.database import async_session_maker
from pindb.database.erasure import erase_user_account
from pindb.database.user import User
from pindb.file_handler import delete_image
from pindb.password_policy import PasswordPolicyError, validate_password
from pindb.templates.admin.users import admin_users_page

router = APIRouter()


async def _render_users_page(
    request: Request,
    current_user_id: int,
    *,
    error: str | None = None,
    password_errors: list[str] | None = None,
    success: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    async with async_session_maker() as session:
        users: Sequence[User] = (
            await session.scalars(select(User).order_by(User.username.asc()))
        ).all()
        return HTMLResponse(
            content=str(
                admin_users_page(
                    request=request,
                    users=users,
                    current_user_id=current_user_id,
                    error=error,
                    password_errors=password_errors,
                    success=success,
                )
            ),
            status_code=status_code,
        )


@router.get("/users")
async def get_admin_users(
    request: Request,
    current_user: AdminUser,
    error: str | None = None,
    success: str | None = None,
) -> HTMLResponse:
    return await _render_users_page(
        request,
        current_user.id,
        error=error,
        success=success,
    )


@router.post("/users/create", response_model=None)
async def create_user(
    request: Request,
    current_user: AdminUser,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    is_editor: Annotated[bool, Form()] = False,
    is_admin: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    """Create a member account.

    This is the only way an account comes into existence: PinDB is a private
    community with no self-service signup. Clashes are reported plainly rather
    than with the unified message a public signup form would need — the actor
    is already an admin, so there is no enumeration to prevent.
    """
    username = username.strip()
    email = email.strip()

    try:
        validate_password(password, username=username, email=email)
    except PasswordPolicyError as exc:
        return await _render_users_page(
            request,
            current_user.id,
            error="Password does not meet the policy.",
            password_errors=exc.rules,
            status_code=400,
        )

    async with async_session_maker.begin() as db:
        if (await db.scalars(select(User).where(User.username == username))).first():
            return await _render_users_page(
                request,
                current_user.id,
                error=f"Username {username!r} is already taken.",
                status_code=400,
            )
        if (await db.scalars(select(User).where(User.email == email))).first():
            return await _render_users_page(
                request,
                current_user.id,
                error=f"Email {email!r} is already registered.",
                status_code=400,
            )
        db.add(
            User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                is_editor=is_editor,
                is_admin=is_admin,
            )
        )

    return RedirectResponse(
        url=f"/admin/users?success={quote(f'Created {username}')}",
        status_code=303,
    )


@router.post("/users/{user_id}/promote")
async def promote_user(user_id: int) -> RedirectResponse:
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_admin = True
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/demote")
async def demote_user(user_id: int, current_user: AdminUser) -> RedirectResponse:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_admin = False
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/promote-editor")
async def promote_editor(user_id: int) -> RedirectResponse:
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_editor = True
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/demote-editor")
async def demote_editor(user_id: int) -> RedirectResponse:
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_editor = False
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete-account")
async def delete_account(user_id: int, current_user: AdminUser) -> RedirectResponse:
    """GDPR-compliant account erasure.

    Anonymises every audit-log reference to the user, drops user-owned
    data (sessions, OAuth links, favorites, owned/wanted pins), demotes
    personal pin sets to global, and hard-deletes the user row.
    Irreversible.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        orphaned_guids = await erase_user_account(session=session, user_id=user_id)
    # See delete_own_account: blob deletion happens after the commit, never
    # inside the transaction.
    for guid in orphaned_guids:
        delete_image(guid)
    return RedirectResponse(url="/admin/users", status_code=303)
