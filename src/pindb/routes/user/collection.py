"""
FastAPI routes: `routes/user/collection.py`.
"""

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.auth import AuthenticatedUser
from pindb.database import Pin, UserOwnedPin, UserWantedPin, async_session_maker
from pindb.templates.get.pin_collection import owned_panel_content, wanted_panel_content

router = APIRouter(prefix="/user/pins", tags=["collection"])


async def _get_owned_entries(
    *,
    session: AsyncSession,
    pin_id: int,
    user_id: int,
) -> list[UserOwnedPin]:
    return list(
        (
            await session.scalars(
                select(UserOwnedPin)
                .where(
                    UserOwnedPin.pin_id == pin_id,
                    UserOwnedPin.user_id == user_id,
                )
                .options(selectinload(UserOwnedPin.grade))
            )
        ).all()
    )


async def _get_wanted_entries(
    *,
    session: AsyncSession,
    pin_id: int,
    user_id: int,
) -> list[UserWantedPin]:
    return list(
        (
            await session.scalars(
                select(UserWantedPin)
                .where(
                    UserWantedPin.pin_id == pin_id,
                    UserWantedPin.user_id == user_id,
                )
                .options(selectinload(UserWantedPin.grade))
            )
        ).all()
    )


async def _render_owned_panel(
    *,
    request: Request,
    pin_id: int,
    user_id: int,
) -> HTMLResponse:
    async with async_session_maker() as session:
        pin: Pin | None = (
            await session.scalars(
                select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
            )
        ).first()
        assert pin is not None
        owned_entries = await _get_owned_entries(
            session=session, pin_id=pin_id, user_id=user_id
        )

        return HTMLResponse(
            content=str(
                owned_panel_content(
                    request=request,
                    pin=pin,
                    owned_entries=owned_entries,
                )
            )
        )


async def _render_wanted_panel(
    *,
    request: Request,
    pin_id: int,
    user_id: int,
) -> HTMLResponse:
    async with async_session_maker() as session:
        pin: Pin | None = (
            await session.scalars(
                select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
            )
        ).first()
        assert pin is not None
        wanted_entries = await _get_wanted_entries(
            session=session, pin_id=pin_id, user_id=user_id
        )

        return HTMLResponse(
            content=str(
                wanted_panel_content(
                    request=request,
                    pin=pin,
                    wanted_entries=wanted_entries,
                )
            )
        )


# ---------------------------------------------------------------------------
# Owned — add
# ---------------------------------------------------------------------------


@router.post(path="/{pin_id}/owned", response_model=None, name="add_owned_pin")
async def add_owned_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
    grade_id: Annotated[int | None, Form()] = None,
    quantity: Annotated[int, Form()] = 1,
) -> Response:
    async with async_session_maker.begin() as db:
        pin: Pin | None = await db.get(entity=Pin, ident=pin_id)
        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        existing: UserOwnedPin | None = (
            await db.scalars(
                select(UserOwnedPin).where(
                    UserOwnedPin.user_id == current_user.id,
                    UserOwnedPin.pin_id == pin_id,
                    UserOwnedPin.grade_id == grade_id,
                )
            )
        ).first()

        if existing is not None:
            existing.quantity = quantity
        else:
            db.add(
                UserOwnedPin(
                    user_id=current_user.id,
                    pin_id=pin_id,
                    grade_id=grade_id,
                    quantity=quantity,
                )
            )

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    return await _render_owned_panel(
        request=request, pin_id=pin_id, user_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Owned — remove
# ---------------------------------------------------------------------------


@router.delete(
    path="/{pin_id}/owned/{entry_id}",
    response_model=None,
    name="remove_owned_pin",
)
async def remove_owned_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    async with async_session_maker.begin() as db:
        entry: UserOwnedPin | None = await db.get(entity=UserOwnedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Owned pin entry not found")
        await db.delete(entry)

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    return await _render_owned_panel(
        request=request, pin_id=pin_id, user_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Owned — update quantity / tradeable
# ---------------------------------------------------------------------------


@router.patch(
    path="/{pin_id}/owned/{entry_id}",
    response_model=None,
    name="update_owned_pin",
)
async def update_owned_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
    quantity: Annotated[int, Form()],
    tradeable_quantity: Annotated[int, Form()],
) -> Response:
    async with async_session_maker.begin() as db:
        entry: UserOwnedPin | None = await db.get(entity=UserOwnedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Owned pin entry not found")

        entry.quantity = max(1, quantity)
        entry.tradeable_quantity = max(0, min(tradeable_quantity, entry.quantity))

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    return await _render_owned_panel(
        request=request, pin_id=pin_id, user_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Wanted — add
# ---------------------------------------------------------------------------


@router.post(path="/{pin_id}/wanted", response_model=None, name="add_wanted_pin")
async def add_wanted_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
    grade_id: Annotated[int | None, Form()] = None,
) -> Response:
    async with async_session_maker.begin() as db:
        pin: Pin | None = await db.get(entity=Pin, ident=pin_id)
        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        existing: UserWantedPin | None = (
            await db.scalars(
                select(UserWantedPin).where(
                    UserWantedPin.user_id == current_user.id,
                    UserWantedPin.pin_id == pin_id,
                    UserWantedPin.grade_id == grade_id,
                )
            )
        ).first()

        if existing is None:
            db.add(
                UserWantedPin(
                    user_id=current_user.id,
                    pin_id=pin_id,
                    grade_id=grade_id,
                )
            )

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    return await _render_wanted_panel(
        request=request, pin_id=pin_id, user_id=current_user.id
    )


# ---------------------------------------------------------------------------
# Wanted — remove
# ---------------------------------------------------------------------------


@router.delete(
    path="/{pin_id}/wanted/{entry_id}",
    response_model=None,
    name="remove_wanted_pin",
)
async def remove_wanted_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    async with async_session_maker.begin() as db:
        entry: UserWantedPin | None = await db.get(entity=UserWantedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Wanted pin entry not found")
        await db.delete(entry)

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    return await _render_wanted_panel(
        request=request, pin_id=pin_id, user_id=current_user.id
    )
