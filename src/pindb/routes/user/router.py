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
from pindb.database import PinSet, User, async_session_maker
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
from pindb.templates.user.profile import user_profile_page
from pindb.templates.user.profile_settings import (
    VALID_DIMENSION_UNITS,
    VALID_THEME_VALUES,
)

router = APIRouter(prefix="/user", tags=["user"])


PROFILE_PREVIEW_LIMIT: int = 10


# ---------------------------------------------------------------------------
# /me — must mount BEFORE /{username} catch-all
# ---------------------------------------------------------------------------


@router.get("/me", response_model=None)
async def get_me(current_user: AuthenticatedUser) -> RedirectResponse:
    return RedirectResponse(url=f"/user/{current_user.username}", status_code=303)


@router.post("/me/settings", response_model=None)
async def update_user_settings(
    current_user: AuthenticatedUser,
    theme: Annotated[str | None, Form()] = None,
    dimension_unit: Annotated[str | None, Form()] = None,
) -> Response:
    if theme is None and dimension_unit is None:
        raise HTTPException(status_code=422, detail="No settings provided")
    if theme is not None and theme not in VALID_THEME_VALUES:
        raise HTTPException(status_code=422, detail="Invalid theme")
    if dimension_unit is not None and dimension_unit not in VALID_DIMENSION_UNITS:
        raise HTTPException(status_code=422, detail="Invalid dimension_unit")
    async with async_session_maker.begin() as db:
        user = await db.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if theme is not None:
            user.theme = theme
        if dimension_unit is not None:
            user.dimension_unit = dimension_unit
    return Response(status_code=204)


@router.post("/me/delete-account", response_model=None, name="delete_own_account")
async def delete_own_account(
    current_user: AuthenticatedUser,
    confirm_username: Annotated[str, Form()],
) -> RedirectResponse:
    """GDPR account erasure initiated by the logged-in user."""
    if confirm_username != current_user.username:
        raise HTTPException(status_code=400, detail="Username does not match")
    async with async_session_maker.begin() as session:
        user: User | None = await session.get(User, current_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        await erase_user_account(session=session, user_id=current_user.id)
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
async def get_user_profile(
    request: Request,
    username: str,
    current_user: CurrentUser,
) -> HTMLResponse:
    async with async_session_maker() as db:
        user: User | None = (
            await db.scalars(select(User).where(User.username == username))
        ).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        favorite_count = await count_favorites(session=db, user_id=user.id)
        favorite_pins = await get_favorite_pins(
            session=db,
            user_id=user.id,
            limit=PROFILE_PREVIEW_LIMIT,
            eager_pin_relationships=True,
        )

        owned_count = await count_owned(session=db, user_id=user.id)
        owned_pins = await get_owned_entries(
            session=db,
            user_id=user.id,
            limit=PROFILE_PREVIEW_LIMIT,
            eager_pin_relationships=True,
        )

        wanted_count = await count_wanted(session=db, user_id=user.id)
        wanted_pins = await get_wanted_entries(
            session=db,
            user_id=user.id,
            limit=PROFILE_PREVIEW_LIMIT,
            eager_pin_relationships=True,
        )

        tradeable_count = await count_owned(
            session=db, user_id=user.id, tradeable_only=True
        )
        tradeable_entries = await get_owned_entries(
            session=db,
            user_id=user.id,
            limit=PROFILE_PREVIEW_LIMIT,
            tradeable_only=True,
            eager_pin_relationships=True,
        )

        personal_sets: list[PinSet] = list(
            (
                await db.scalars(
                    select(PinSet)
                    .where(PinSet.owner_id == user.id)
                    .order_by(PinSet.name)
                )
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
