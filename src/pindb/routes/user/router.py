from typing import Annotated, Any

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.engine.row import Row

from pindb.auth import AdminUser, AuthenticatedUser, CurrentUser
from pindb.database import Pin, PinSet, User, session_maker
from pindb.database.joins import (
    pin_set_memberships,
    user_favorite_pin_sets,
    user_favorite_pins,
)
from pindb.search.search import search_pin
from pindb.templates.user.profile import user_profile_page

router = APIRouter(prefix="/user", tags=["user"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_can_edit_set(pin_set: PinSet, user: User) -> None:
    if pin_set.owner_id is None:
        # Global set — owner_id=NULL convention; only admins can edit
        if not user.is_admin:
            raise HTTPException(
                status_code=403, detail="Admin access required to edit global sets"
            )
    else:
        # Personal set — must be the owner
        if pin_set.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You do not own this pin set")


# ---------------------------------------------------------------------------
# /me redirect — must be registered BEFORE /{username} to avoid shadowing
# ---------------------------------------------------------------------------


@router.get("/me", response_model=None)
def get_me(current_user: AuthenticatedUser) -> RedirectResponse:
    return RedirectResponse(url=f"/user/{current_user.username}", status_code=303)


@router.get("/me/sets", response_model=None)
def get_my_sets(
    request: Request,
    current_user: AuthenticatedUser,
) -> HTMLResponse:
    with session_maker() as db:
        personal_sets: list[PinSet] = list(
            db.scalars(
                select(PinSet)
                .where(PinSet.owner_id == current_user.id)
                .order_by(PinSet.name)
            ).all()
        )

    from pindb.templates.create_and_edit.user_pin_sets import user_pin_sets_page

    return HTMLResponse(
        content=str(user_pin_sets_page(request=request, sets=personal_sets))
    )


# ---------------------------------------------------------------------------
# Public user profile
# ---------------------------------------------------------------------------


@router.get("/{username}", response_model=None)
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

        favorite_pins: list[Pin] = list(
            db.scalars(
                select(Pin)
                .join(user_favorite_pins, Pin.id == user_favorite_pins.c.pin_id)
                .where(user_favorite_pins.c.user_id == user.id)
                .order_by(Pin.name)
            ).all()
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
                    personal_sets=personal_sets,
                    current_user=current_user,
                )
            )
        )


# ---------------------------------------------------------------------------
# Edit personal set
# ---------------------------------------------------------------------------


@router.get("/sets/{set_id}/edit", response_model=None)
def get_edit_set(
    request: Request,
    set_id: int,
    current_user: AuthenticatedUser,
) -> HTMLResponse:
    with session_maker() as db:
        pin_set = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)

        pins: list[Pin] = list(
            db.scalars(
                select(Pin)
                .join(pin_set_memberships, Pin.id == pin_set_memberships.c.pin_id)
                .where(pin_set_memberships.c.set_id == set_id)
                .order_by(pin_set_memberships.c.position)
            ).all()
        )

    from pindb.templates.create_and_edit.pin_set import pin_set_edit_page

    return HTMLResponse(
        content=str(
            pin_set_edit_page(
                request=request,
                pin_set=pin_set,
                pins=pins,
                current_user=current_user,
            )
        )
    )


@router.post("/sets/{set_id}/edit", response_model=None)
def update_set(
    request: Request,
    set_id: int,
    current_user: AuthenticatedUser,
    name: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        pin_set.name: str = name.strip()
        pin_set.description: str | None = description.strip() if description else None

        pins: list[Pin] = list(
            db.scalars(
                select(Pin)
                .join(pin_set_memberships, Pin.id == pin_set_memberships.c.pin_id)
                .where(pin_set_memberships.c.set_id == set_id)
                .order_by(pin_set_memberships.c.position)
            ).all()
        )

    from pindb.templates.create_and_edit.pin_set import pin_set_edit_page

    return HTMLResponse(
        content=str(
            pin_set_edit_page(
                request=request,
                pin_set=pin_set,
                pins=pins,
                current_user=current_user,
            )
        )
    )


@router.post("/sets/{set_id}/pins/reorder", response_model=None)
def reorder_set_pins(
    set_id: int,
    current_user: AuthenticatedUser,
    pin_ids: Annotated[list[int], Form()],
) -> Response:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)

        for position, pin_id in enumerate(pin_ids):
            db.execute(
                pin_set_memberships.update()
                .where(
                    pin_set_memberships.c.set_id == set_id,
                    pin_set_memberships.c.pin_id == pin_id,
                )
                .values(position=position)
            )

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Promote personal set to global
# ---------------------------------------------------------------------------


@router.post("/sets/{set_id}/promote", response_model=None)
def promote_set_to_global(
    request: Request,
    set_id: int,
    _current_user: AdminUser,
) -> RedirectResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        if pin_set.owner_id is None:
            raise HTTPException(status_code=400, detail="Set is already global")
        # Setting owner_id to NULL promotes this set to "global" status.
        # Global sets (owner_id IS NULL) are curator/admin sets visible to all users.
        pin_set.owner_id = None

    return RedirectResponse(
        url=str(request.url_for("get_list_pin_sets")),
        status_code=303,
    )


# ---------------------------------------------------------------------------
# Favorites — Pins
# ---------------------------------------------------------------------------


@router.post("/favorites/pins/{pin_id}", response_model=None)
def favorite_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        pin: Pin | None = db.get(Pin, pin_id)
        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")
        user: User | None = db.get(User, current_user.id)
        assert user is not None
        user.favorite_pins.add(pin)

    if request.headers.get("HX-Request"):
        from pindb.templates.get.pin import favorite_button

        return HTMLResponse(
            content=str(
                favorite_button(request=request, pin_id=pin_id, is_favorited=True)
            )
        )
    return Response(status_code=204)


@router.delete("/favorites/pins/{pin_id}", response_model=None)
def unfavorite_pin(
    request: Request,
    pin_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        db.execute(
            user_favorite_pins.delete().where(
                user_favorite_pins.c.user_id == current_user.id,
                user_favorite_pins.c.pin_id == pin_id,
            )
        )

    if request.headers.get("HX-Request"):
        from pindb.templates.get.pin import favorite_button

        return HTMLResponse(
            content=str(
                favorite_button(request=request, pin_id=pin_id, is_favorited=False)
            )
        )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Favorites — Pin Sets
# ---------------------------------------------------------------------------


@router.post("/favorites/sets/{set_id}", response_model=None)
def favorite_set(
    set_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        user: User | None = db.get(User, current_user.id)
        assert user is not None
        user.favorite_pin_sets.add(pin_set)
    return Response(status_code=204)


@router.delete("/favorites/sets/{set_id}", response_model=None)
def unfavorite_set(
    set_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        db.execute(
            user_favorite_pin_sets.delete().where(
                user_favorite_pin_sets.c.user_id == current_user.id,
                user_favorite_pin_sets.c.pin_set_id == set_id,
            )
        )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Personal Sets — CRUD
# ---------------------------------------------------------------------------


@router.post("/me/sets", response_model=None)
def create_personal_set(
    request: Request,
    current_user: AuthenticatedUser,
    name: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
) -> RedirectResponse:
    with session_maker.begin() as db:
        pin_set = PinSet(
            name=name.strip(),
            description=description.strip() if description else None,
            owner_id=current_user.id,
        )
        db.add(pin_set)
        db.flush()
        set_id = pin_set.id

    return RedirectResponse(
        url=str(request.url_for("get_edit_set", set_id=set_id)),
        status_code=303,
    )


@router.post("/sets/{set_id}/delete", response_model=None)
def delete_personal_set(
    request: Request,
    set_id: int,
    current_user: AuthenticatedUser,
) -> RedirectResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        db.delete(pin_set)

    return RedirectResponse(
        url=str(request.url_for("get_my_sets")),
        status_code=303,
    )


# ---------------------------------------------------------------------------
# Personal Sets — Pin membership
# ---------------------------------------------------------------------------


@router.post("/sets/{set_id}/pins/{pin_id}", response_model=None)
def add_pin_to_personal_set(
    request: Request,
    set_id: int,
    pin_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        if db.get(Pin, pin_id) is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        # Check not already a member
        already: Row[Any] | None = db.execute(
            select(pin_set_memberships).where(
                pin_set_memberships.c.set_id == set_id,
                pin_set_memberships.c.pin_id == pin_id,
            )
        ).first()
        if already is None:
            max_pos = db.scalar(
                select(
                    func.coalesce(func.max(pin_set_memberships.c.position), -1)
                ).where(pin_set_memberships.c.set_id == set_id)
            )
            db.execute(
                pin_set_memberships.insert().values(
                    set_id=set_id, pin_id=pin_id, position=(max_pos or 0) + 1
                )
            )

    if request.headers.get("HX-Request"):
        hx_target: str = request.headers.get("HX-Target", "")
        if hx_target.startswith("search-row-"):
            with session_maker() as db:
                pin = db.get(Pin, pin_id)
                assert pin is not None
                count = db.scalar(
                    select(func.count()).where(pin_set_memberships.c.set_id == set_id)
                )
            from pindb.templates.create_and_edit.pin_set import (
                pin_card_oob,
                pin_count_oob,
                pin_empty_oob,
                search_result_row,
            )

            parts: list[str] = [
                str(
                    search_result_row(
                        request=request, pin=pin, set_id=set_id, in_set=True
                    )
                ),
                str(pin_card_oob(request=request, pin=pin, set_id=set_id)),
                str(pin_count_oob(count or 0)),
            ]
            if count == 1:
                parts.append(str(pin_empty_oob()))
            return HTMLResponse(content="".join(parts))
        else:
            with session_maker() as db:
                pin_set = db.get(PinSet, set_id)
                assert pin_set is not None
            from pindb.templates.get.pin import set_row

            return HTMLResponse(
                content=str(
                    set_row(
                        request=request, pin_id=pin_id, pin_set=pin_set, in_set=True
                    )
                )
            )
    return Response(status_code=204)


@router.delete("/sets/{set_id}/pins/{pin_id}", response_model=None)
def remove_pin_from_personal_set(
    request: Request,
    set_id: int,
    pin_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        db.execute(
            pin_set_memberships.delete().where(
                pin_set_memberships.c.set_id == set_id,
                pin_set_memberships.c.pin_id == pin_id,
            )
        )

    if request.headers.get("HX-Request"):
        hx_target: str = request.headers.get("HX-Target", "")
        if hx_target.startswith("pin-row-"):
            # X button on pin card in the set editor — remove the card and update count
            with session_maker() as db:
                count = db.scalar(
                    select(func.count()).where(pin_set_memberships.c.set_id == set_id)
                )
            from pindb.templates.create_and_edit.pin_set import pin_count_oob

            return HTMLResponse(content=str(pin_count_oob(count or 0)))
        elif hx_target.startswith("search-row-"):
            with session_maker() as db:
                pin = db.get(Pin, pin_id)
                assert pin is not None
            from pindb.templates.create_and_edit.pin_set import search_result_row

            return HTMLResponse(
                content=str(
                    search_result_row(
                        request=request, pin=pin, set_id=set_id, in_set=False
                    )
                )
            )
        else:
            with session_maker() as db:
                pin_set: PinSet | None = db.get(PinSet, set_id)
                assert pin_set is not None
            from pindb.templates.get.pin import set_row

            return HTMLResponse(
                content=str(
                    set_row(
                        request=request, pin_id=pin_id, pin_set=pin_set, in_set=False
                    )
                )
            )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Edit set — pin search (HTMX fragment)
# ---------------------------------------------------------------------------


@router.get("/sets/{set_id}/pin-search", response_model=None)
def search_pins_for_set(
    request: Request,
    set_id: int,
    current_user: AuthenticatedUser,
    query: str = "",
) -> HTMLResponse:
    with session_maker() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)

        results: list[Pin] = []
        if query.strip():
            results = search_pin(query=query.strip(), session=db) or []
        existing_ids: set[int] = set(
            db.scalars(
                select(pin_set_memberships.c.pin_id).where(
                    pin_set_memberships.c.set_id == set_id
                )
            ).all()
        )

    from pindb.templates.create_and_edit.pin_set import pin_search_results

    return HTMLResponse(
        content=str(
            pin_search_results(
                request=request,
                set_id=set_id,
                pins=results,
                existing_ids=existing_ids,
            )
        )
    )
