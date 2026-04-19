"""Top-level user router.

Aggregates the smaller per-concern routers (lists, sets) and exposes the
public profile page + the ``/me`` endpoints. Order matters: ``/me`` and the
sets/lists routers must mount before the catch-all ``/{username}`` route.
"""

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import AuthenticatedUser, CurrentUser, clear_session_cookie
from pindb.database import PinSet, User, session_maker
from pindb.database.erasure import erase_user_account
from pindb.database.user_pin_queries import (
    count_favorites,
    count_owned,
    count_wanted,
    get_favorite_pins,
    get_owned_entries,
    get_wanted_entries,
)
from pindb.routes.user.lists import router as lists_router
from pindb.routes.user.sets import router as sets_router
from pindb.templates.user.profile import VALID_THEME_VALUES, user_profile_page

router = APIRouter(prefix="/user", tags=["user"])


PROFILE_PREVIEW_LIMIT: int = 10


# ---------------------------------------------------------------------------
# /me — must mount BEFORE /{username} catch-all
# ---------------------------------------------------------------------------


@router.get("/me", response_model=None)
def get_me(current_user: AuthenticatedUser) -> RedirectResponse:
    return RedirectResponse(url=f"/user/{current_user.username}", status_code=303)


@router.post("/me/settings", response_model=None)
def update_user_settings(
    current_user: AuthenticatedUser,
    theme: Annotated[str, Form()],
) -> Response:
    if theme not in VALID_THEME_VALUES:
        raise HTTPException(status_code=422, detail="Invalid theme")
    with session_maker.begin() as db:
        user = db.get(User, current_user.id)
        if user is not None:
            user.theme = theme
    return Response(status_code=204)


@router.post("/me/delete-account", response_model=None, name="delete_own_account")
def delete_own_account(
    current_user: AuthenticatedUser,
    confirm_username: Annotated[str, Form()],
) -> RedirectResponse:
    """GDPR account erasure initiated by the logged-in user."""
    if confirm_username != current_user.username:
        raise HTTPException(status_code=400, detail="Username does not match")
    with session_maker.begin() as session:
        user: User | None = session.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        erase_user_account(session=session, user_id=current_user.id)
    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


# Mount sub-routers BEFORE the catch-all profile route so that paths like
# /user/me/sets/new and /user/{username}/favorites resolve to them first.
router.include_router(sets_router)
router.include_router(lists_router)


# ---------------------------------------------------------------------------
# Public profile page
# ---------------------------------------------------------------------------


@router.get("/{username}", response_model=None, name="get_user_profile")
def get_user_profile(
    request: Request,
    username: str,
    current_user: CurrentUser,
) -> HTMLResponse:
    with session_maker() as db:
        user: User | None = db.scalars(
            select(User).where(User.username == username)
        ).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        favorite_count = count_favorites(session=db, user_id=user.id)
        favorite_pins = get_favorite_pins(
            session=db, user_id=user.id, limit=PROFILE_PREVIEW_LIMIT
        )

        owned_count = count_owned(session=db, user_id=user.id)
        owned_pins = get_owned_entries(
            session=db, user_id=user.id, limit=PROFILE_PREVIEW_LIMIT
        )

        wanted_count = count_wanted(session=db, user_id=user.id)
        wanted_pins = get_wanted_entries(
            session=db, user_id=user.id, limit=PROFILE_PREVIEW_LIMIT
        )

        tradeable_count = count_owned(session=db, user_id=user.id, tradeable_only=True)
        tradeable_entries = get_owned_entries(
            session=db,
            user_id=user.id,
            limit=PROFILE_PREVIEW_LIMIT,
            tradeable_only=True,
        )

        personal_sets: list[PinSet] = list(
            db.scalars(
                select(PinSet).where(PinSet.owner_id == user.id).order_by(PinSet.name)
            ).all()
        )

        return HTMLResponse(
            content=str(
                user_profile_page(
                    request=request,
                    profile_user=user,
                    favorite_pins=favorite_pins,
                    favorite_count=favorite_count,
                    personal_sets=personal_sets,
                    owned_pins=owned_pins,
                    owned_count=owned_count,
                    wanted_pins=wanted_pins,
                    wanted_count=wanted_count,
                    tradeable_entries=tradeable_entries,
                    tradeable_count=tradeable_count,
                    current_user=current_user,
                )
            )
        )
