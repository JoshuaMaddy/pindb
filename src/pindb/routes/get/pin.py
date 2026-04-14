from fastapi import Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import CurrentUser
from pindb.database import Pin, PinSet, User, UserOwnedPin, UserWantedPin, session_maker
from pindb.database.joins import user_favorite_pins
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
    has_pending_edits,
)
from pindb.templates.get.pin import pin_page

router = APIRouter()


@router.get(path="/pin/{id}", response_model=None)
def get_pin(
    request: Request,
    id: int,
    current_user: CurrentUser,
    version: str | None = Query(default=None),
) -> HTMLResponse | RedirectResponse:
    can_see_pending = current_user is not None and (
        current_user.is_editor or current_user.is_admin
    )
    viewing_pending: bool = version == "pending" and can_see_pending

    with session_maker() as session:
        pin_obj: Pin | None = session.scalar(
            select(Pin)
            .where(Pin.id == id)
            .options(
                selectinload(Pin.shops),
                selectinload(Pin.tags),
                selectinload(Pin.artists),
                selectinload(Pin.sets),
                selectinload(Pin.links),
                selectinload(Pin.grades),
                selectinload(Pin.currency),
            )
        )

        if not pin_obj:
            return RedirectResponse(url="/")

        pending_chain_exists: bool = can_see_pending and has_pending_edits(
            session, "pins", id
        )

        if viewing_pending and pending_chain_exists:
            chain = get_edit_chain(session, "pins", id)
            effective = get_effective_snapshot(pin_obj, chain)
            with session.no_autoflush:
                apply_snapshot_in_memory(pin_obj, effective, session)

        is_favorited = False
        user_sets: list[PinSet] = []
        owned_entries: list[UserOwnedPin] = []
        wanted_entries: list[UserWantedPin] = []

        if current_user is not None:
            user: User | None = session.get(User, current_user.id)
            if user is not None:
                is_favorited = bool(
                    session.execute(
                        select(user_favorite_pins).where(
                            user_favorite_pins.c.user_id == current_user.id,
                            user_favorite_pins.c.pin_id == id,
                        )
                    ).first()
                )
                user_sets = list(
                    session.scalars(
                        select(PinSet).where(PinSet.owner_id == current_user.id)
                    ).all()
                )
                owned_entries = list(
                    session.scalars(
                        select(UserOwnedPin)
                        .where(
                            UserOwnedPin.user_id == current_user.id,
                            UserOwnedPin.pin_id == id,
                        )
                        .options(selectinload(UserOwnedPin.grade))
                    ).all()
                )
                wanted_entries = list(
                    session.scalars(
                        select(UserWantedPin)
                        .where(
                            UserWantedPin.user_id == current_user.id,
                            UserWantedPin.pin_id == id,
                        )
                        .options(selectinload(UserWantedPin.grade))
                    ).all()
                )

        return HTMLResponse(
            content=pin_page(
                request=request,
                pin=pin_obj,
                is_favorited=is_favorited,
                user_sets=user_sets,
                owned_entries=owned_entries,
                wanted_entries=wanted_entries,
                has_pending_chain=pending_chain_exists,
                viewing_pending=viewing_pending,
            )
        )
