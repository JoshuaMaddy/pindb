"""User pin list pages: favorites, collection, wants, trades.

All four routes share a single profile-user lookup + pagination wrapper; the
per-list count and entry queries live in ``database/user_pin_queries``.
"""

from typing import Callable, TypeVar

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy import Element
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindb.database import User, session_maker
from pindb.database.user_pin_queries import (
    count_favorites,
    count_owned,
    count_wanted,
    get_favorite_pins,
    get_owned_entries,
    get_wanted_entries,
)
from pindb.templates.user.pin_list_pages import (
    PAGE_SIZE,
    ViewMode,
    collection_list_page,
    favorites_list_page,
    trades_list_page,
    wants_list_page,
)

router = APIRouter(tags=["user"])


_T = TypeVar("_T")


def _resolved_view(view: str) -> ViewMode:
    return "table" if view == "table" else "grid"


def _load_profile_user(*, session: Session, username: str) -> User:
    user: User | None = session.scalars(
        select(User).where(User.username == username)
    ).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _render_pin_list(
    *,
    request: Request,
    username: str,
    page: int,
    view: str,
    fetch: Callable[[Session, User, int, int], tuple[int, _T]],
    render: Callable[[Request, User, _T, int, int, ViewMode], Element],
) -> HTMLResponse:
    page = max(1, page)
    resolved_view = _resolved_view(view)
    offset = (page - 1) * PAGE_SIZE

    with session_maker() as session:
        user = _load_profile_user(session=session, username=username)
        total, payload = fetch(session, user, PAGE_SIZE, offset)

    return HTMLResponse(
        content=str(render(request, user, payload, total, page, resolved_view))
    )


@router.get("/{username}/favorites", response_model=None, name="user_favorites_list")
def user_favorites_list(
    request: Request,
    username: str,
    page: int = 1,
    view: str = "grid",
) -> HTMLResponse:
    def fetch(session: Session, user: User, limit: int, offset: int):
        return (
            count_favorites(session=session, user_id=user.id),
            get_favorite_pins(
                session=session,
                user_id=user.id,
                limit=limit,
                offset=offset,
                eager_pin_relationships=True,
            ),
        )

    return _render_pin_list(
        request=request,
        username=username,
        page=page,
        view=view,
        fetch=fetch,
        render=lambda request, user, pins, total, page, view: favorites_list_page(
            request=request,
            profile_user=user,
            pins=pins,
            total=total,
            page=page,
            view=view,
        ),
    )


@router.get("/{username}/collection", response_model=None, name="user_collection_list")
def user_collection_list(
    request: Request,
    username: str,
    page: int = 1,
    view: str = "grid",
) -> HTMLResponse:
    def fetch(session: Session, user: User, limit: int, offset: int):
        return (
            count_owned(session=session, user_id=user.id),
            get_owned_entries(
                session=session,
                user_id=user.id,
                limit=limit,
                offset=offset,
                eager_pin_relationships=True,
            ),
        )

    return _render_pin_list(
        request=request,
        username=username,
        page=page,
        view=view,
        fetch=fetch,
        render=lambda request, user, owned_pins, total, page, view: (
            collection_list_page(
                request=request,
                profile_user=user,
                owned_pins=owned_pins,
                total=total,
                page=page,
                view=view,
            )
        ),
    )


@router.get("/{username}/wants", response_model=None, name="user_wants_list")
def user_wants_list(
    request: Request,
    username: str,
    page: int = 1,
    view: str = "grid",
) -> HTMLResponse:
    def fetch(session: Session, user: User, limit: int, offset: int):
        return (
            count_wanted(session=session, user_id=user.id),
            get_wanted_entries(
                session=session,
                user_id=user.id,
                limit=limit,
                offset=offset,
                eager_pin_relationships=True,
            ),
        )

    return _render_pin_list(
        request=request,
        username=username,
        page=page,
        view=view,
        fetch=fetch,
        render=lambda request, user, wanted_pins, total, page, view: wants_list_page(
            request=request,
            profile_user=user,
            wanted_pins=wanted_pins,
            total=total,
            page=page,
            view=view,
        ),
    )


@router.get("/{username}/trades", response_model=None, name="user_trades_list")
def user_trades_list(
    request: Request,
    username: str,
    page: int = 1,
    view: str = "grid",
) -> HTMLResponse:
    def fetch(session: Session, user: User, limit: int, offset: int):
        return (
            count_owned(session=session, user_id=user.id, tradeable_only=True),
            get_owned_entries(
                session=session,
                user_id=user.id,
                limit=limit,
                offset=offset,
                tradeable_only=True,
                eager_pin_relationships=True,
            ),
        )

    return _render_pin_list(
        request=request,
        username=username,
        page=page,
        view=view,
        fetch=fetch,
        render=lambda request, user, tradeable_entries, total, page, view: (
            trades_list_page(
                request=request,
                profile_user=user,
                tradeable_entries=tradeable_entries,
                total=total,
                page=page,
                view=view,
            )
        ),
    )
