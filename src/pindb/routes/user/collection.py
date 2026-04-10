from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import AuthenticatedUser
from pindb.database import Pin, UserOwnedPin, UserWantedPin, session_maker

router = APIRouter(prefix="/user/pins", tags=["collection"])


def _get_owned_entries(
    db,
    pin_id: int,
    user_id: int,
) -> list[UserOwnedPin]:
    return list(
        db.scalars(
            select(UserOwnedPin)
            .where(
                UserOwnedPin.pin_id == pin_id,
                UserOwnedPin.user_id == user_id,
            )
            .options(selectinload(UserOwnedPin.grade))
        ).all()
    )


def _get_wanted_entries(
    db,
    pin_id: int,
    user_id: int,
) -> list[UserWantedPin]:
    return list(
        db.scalars(
            select(UserWantedPin)
            .where(
                UserWantedPin.pin_id == pin_id,
                UserWantedPin.user_id == user_id,
            )
            .options(selectinload(UserWantedPin.grade))
        ).all()
    )


# ---------------------------------------------------------------------------
# Owned — add
# ---------------------------------------------------------------------------


@router.post(path="/{pin_id}/owned", response_model=None, name="add_owned_pin")
def add_owned_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
    grade_id: Annotated[int | None, Form()] = None,
    quantity: Annotated[int, Form()] = 1,
) -> Response:
    with session_maker.begin() as db:
        pin: Pin | None = db.get(entity=Pin, ident=pin_id)
        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        # Check for existing entry (same user/pin/grade)
        existing: UserOwnedPin | None = db.scalars(
            select(UserOwnedPin).where(
                UserOwnedPin.user_id == current_user.id,
                UserOwnedPin.pin_id == pin_id,
                UserOwnedPin.grade_id == grade_id,
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

    from pindb.templates.get.pin_collection import owned_panel_content

    with session_maker() as db:
        pin = db.scalars(
            select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
        ).first()
        assert pin is not None
        owned_entries: list[UserOwnedPin] = _get_owned_entries(
            db=db,
            pin_id=pin_id,
            user_id=current_user.id,
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


# ---------------------------------------------------------------------------
# Owned — remove
# ---------------------------------------------------------------------------


@router.delete(
    path="/{pin_id}/owned/{entry_id}",
    response_model=None,
    name="remove_owned_pin",
)
def remove_owned_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        entry: UserOwnedPin | None = db.get(entity=UserOwnedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Owned pin entry not found")
        db.delete(entry)

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    from pindb.templates.get.pin_collection import owned_panel_content

    with session_maker() as db:
        pin: Pin | None = db.scalars(
            select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
        ).first()
        assert pin is not None
        owned_entries: list[UserOwnedPin] = _get_owned_entries(
            db=db,
            pin_id=pin_id,
            user_id=current_user.id,
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


# ---------------------------------------------------------------------------
# Owned — update quantity / tradeable
# ---------------------------------------------------------------------------


@router.patch(
    path="/{pin_id}/owned/{entry_id}",
    response_model=None,
    name="update_owned_pin",
)
def update_owned_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
    quantity: Annotated[int, Form()],
    tradeable_quantity: Annotated[int, Form()],
) -> Response:
    with session_maker.begin() as db:
        entry: UserOwnedPin | None = db.get(entity=UserOwnedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Owned pin entry not found")

        entry.quantity = max(1, quantity)
        entry.tradeable_quantity = max(0, min(tradeable_quantity, entry.quantity))

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    from pindb.templates.get.pin_collection import owned_panel_content

    with session_maker() as db:
        pin: Pin | None = db.scalars(
            select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
        ).first()
        assert pin is not None
        owned_entries: list[UserOwnedPin] = _get_owned_entries(
            db=db,
            pin_id=pin_id,
            user_id=current_user.id,
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


# ---------------------------------------------------------------------------
# Wanted — add
# ---------------------------------------------------------------------------


@router.post(path="/{pin_id}/wanted", response_model=None, name="add_wanted_pin")
def add_wanted_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
    grade_id: Annotated[int | None, Form()] = None,
) -> Response:
    with session_maker.begin() as db:
        pin: Pin | None = db.get(entity=Pin, ident=pin_id)
        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        existing: UserWantedPin | None = db.scalars(
            select(UserWantedPin).where(
                UserWantedPin.user_id == current_user.id,
                UserWantedPin.pin_id == pin_id,
                UserWantedPin.grade_id == grade_id,
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

    from pindb.templates.get.pin_collection import wanted_panel_content

    with session_maker() as db:
        pin = db.scalars(
            select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
        ).first()
        assert pin is not None
        wanted_entries: list[UserWantedPin] = _get_wanted_entries(
            db=db,
            pin_id=pin_id,
            user_id=current_user.id,
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
# Wanted — remove
# ---------------------------------------------------------------------------


@router.delete(
    path="/{pin_id}/wanted/{entry_id}",
    response_model=None,
    name="remove_wanted_pin",
)
def remove_wanted_pin(
    request: Request,
    pin_id: int,
    entry_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        entry: UserWantedPin | None = db.get(entity=UserWantedPin, ident=entry_id)
        if entry is None or entry.pin_id != pin_id or entry.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Wanted pin entry not found")
        db.delete(entry)

    if not request.headers.get("HX-Request"):
        return Response(status_code=204)

    from pindb.templates.get.pin_collection import wanted_panel_content

    with session_maker() as db:
        pin: Pin | None = db.scalars(
            select(Pin).where(Pin.id == pin_id).options(selectinload(Pin.grades))
        ).first()
        assert pin is not None
        wanted_entries: list[UserWantedPin] = _get_wanted_entries(
            db=db,
            pin_id=pin_id,
            user_id=current_user.id,
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
