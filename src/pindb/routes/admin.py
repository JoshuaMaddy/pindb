from typing import Sequence
from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pindb.auth import AdminUser, require_admin
from pindb.database import Artist, Material, Pin, PinSet, Shop, Tag, session_maker
from pindb.database.user import User
from pindb.search.update import update_all
from pindb.templates.admin.index import admin_panel_page
from pindb.templates.admin.users import admin_users_page

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def _count_pending(session: Session) -> int:
    opts: dict[str, bool] = {"include_pending": True}
    total = 0
    for model in [Pin, Shop, Artist, Tag, Material, PinSet]:
        count = session.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.approved_at.is_(None),  # type: ignore[attr-defined]
                model.rejected_at.is_(None),  # type: ignore[attr-defined]
                model.deleted_at.is_(None),  # type: ignore[attr-defined]
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        )
        total += count or 0
    return total


@router.get("")
def get_admin_panel(request: Request) -> HTMLResponse:
    with session_maker() as session:
        pending_count = _count_pending(session)
    return HTMLResponse(
        content=str(admin_panel_page(request=request, pending_count=pending_count))
    )


@router.post("/search/sync")
def sync_search_index() -> HTMLResponse:
    update_all()
    return HTMLResponse(content="Search index sync triggered.")


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
