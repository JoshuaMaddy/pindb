"""
FastAPI routes: `routes/admin/users.py`.
"""

from typing import Sequence

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import AdminUser
from pindb.database import session_maker
from pindb.database.erasure import erase_user_account
from pindb.database.user import User
from pindb.templates.admin.users import admin_users_page

router = APIRouter()


@router.get("/users")
def get_admin_users(request: Request, current_user: AdminUser) -> HTMLResponse:
    with session_maker() as session:
        users: Sequence[User] = session.scalars(
            select(User).order_by(User.username.asc())
        ).all()
        return HTMLResponse(
            content=str(
                admin_users_page(
                    request=request,
                    users=users,
                    current_user_id=current_user.id,
                )
            )
        )


@router.post("/users/{user_id}/promote")
def promote_user(user_id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        user: User | None = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_admin = True
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/demote")
def demote_user(user_id: int, current_user: AdminUser) -> RedirectResponse:
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")
    with session_maker.begin() as session:
        user: User | None = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_admin = False
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/promote-editor")
def promote_editor(user_id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        user: User | None = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_editor = True
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/demote-editor")
def demote_editor(user_id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        user: User | None = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_editor = False
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete-account")
def delete_account(user_id: int, current_user: AdminUser) -> RedirectResponse:
    """GDPR-compliant account erasure.

    Anonymises every audit-log reference to the user, drops user-owned
    data (sessions, OAuth links, favorites, owned/wanted pins), demotes
    personal pin sets to global, and hard-deletes the user row.
    Irreversible.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    with session_maker.begin() as session:
        user: User | None = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        erase_user_account(session=session, user_id=user_id)
    return RedirectResponse(url="/admin/users", status_code=303)
