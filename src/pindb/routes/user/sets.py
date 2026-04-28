"""Personal & global PinSet CRUD, pin-membership, favorites, search."""

from typing import Annotated, Any

from fastapi import Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import func, select
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import selectinload

from pindb.auth import AdminUser, AuthenticatedUser
from pindb.database import Pin, PinSet, User, session_maker
from pindb.database.joins import (
    pin_set_memberships,
    user_favorite_pin_sets,
    user_favorite_pins,
)
from pindb.htmx_toast import redirect_or_htmx_toast
from pindb.routes._name_check import (
    NameCheckKind,
    duplicate_name_response,
    empty_name_check_response,
    normalized_name_exists,
    normalized_name_key,
)
from pindb.search.search import search_pin
from pindb.templates.create_and_edit.pin_set import (
    pin_card_oob,
    pin_count_oob,
    pin_empty_oob,
    pin_search_results,
    pin_set_edit_page,
    search_result_row,
)
from pindb.templates.create_and_edit.user_pin_sets import create_user_set_page
from pindb.templates.get.pin import favorite_button, set_row

router = APIRouter(tags=["user"])


def _assert_can_edit_set(pin_set: PinSet, user: User) -> None:
    if pin_set.owner_id is None:
        if not user.is_admin:
            raise HTTPException(
                status_code=403, detail="Admin access required to edit global sets"
            )
    elif pin_set.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this pin set")


# ---------------------------------------------------------------------------
# Personal set creation page
# ---------------------------------------------------------------------------


@router.get("/me/sets/new", response_model=None)
def get_create_user_set(
    request: Request,
    _current_user: AuthenticatedUser,
) -> HtpyResponse:
    return HtpyResponse(create_user_set_page(request=request))


@router.get("/me/sets/check-name", response_model=None)
def get_personal_set_check_name(
    current_user: AuthenticatedUser,
    name: str = Query(default=""),
    exclude_id: int | None = Query(default=None),
) -> HTMLResponse:
    normalized_name: str = normalized_name_key(name=name)
    if not normalized_name:
        return empty_name_check_response()

    with session_maker() as db:
        exists: bool = normalized_name_exists(
            session=db,
            kind=NameCheckKind.pin_set,
            normalized_name=normalized_name,
            exclude_id=exclude_id,
            owner_id=current_user.id,
            include_pending=True,
        )

    if not exists:
        return empty_name_check_response()
    return duplicate_name_response(name=name)


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
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        pin_set.name = name.strip()
        pin_set.description = description.strip() if description else None
        is_global: bool = pin_set.owner_id is None

    if is_global:
        back_url = str(request.url_for("get_list_pin_sets"))
    else:
        back_url = str(
            request.url_for("get_user_profile", username=current_user.username)
        )

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=back_url,
        message="Pin set updated.",
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
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        if pin_set.owner_id is None:
            raise HTTPException(status_code=400, detail="Set is already global")
        # owner_id=None ⇒ global, visible to all
        pin_set.owner_id = None

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(request.url_for("get_list_pin_sets")),
        message="Set promoted to global.",
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
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as db:
        pin_set = PinSet(
            name=name.strip(),
            description=description.strip() if description else None,
            owner_id=current_user.id,
        )
        db.add(pin_set)
        db.flush()
        set_id = pin_set.id

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(request.url_for("get_edit_set", set_id=set_id)),
        message="Set created.",
    )


@router.post("/sets/{set_id}/delete", response_model=None)
def delete_personal_set(
    request: Request,
    set_id: int,
    current_user: AuthenticatedUser,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)
        db.delete(pin_set)

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(
            request.url_for("get_user_profile", username=current_user.username)
        ),
        message="Set deleted.",
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
                pin = db.scalar(
                    select(Pin)
                    .where(Pin.id == pin_id)
                    .options(selectinload(Pin.shops), selectinload(Pin.artists))
                )
                assert pin is not None
                count = db.scalar(
                    select(func.count()).where(pin_set_memberships.c.set_id == set_id)
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

            return HtpyResponse(
                set_row(request=request, pin_id=pin_id, pin_set=pin_set, in_set=True)
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
            with session_maker() as db:
                count = db.scalar(
                    select(func.count()).where(pin_set_memberships.c.set_id == set_id)
                )

            return HtpyResponse(pin_count_oob(count or 0))
        elif hx_target.startswith("search-row-"):
            with session_maker() as db:
                pin = db.scalar(
                    select(Pin)
                    .where(Pin.id == pin_id)
                    .options(selectinload(Pin.shops), selectinload(Pin.artists))
                )
                assert pin is not None

            return HTMLResponse(
                content=str(
                    search_result_row(
                        request=request, pin=pin, set_id=set_id, in_set=False
                    )
                )
            )
        else:
            with session_maker() as db:
                pin_set = db.get(PinSet, set_id)
                assert pin_set is not None

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
    q: str = "",
) -> HTMLResponse:
    with session_maker() as db:
        pin_set: PinSet | None = db.get(PinSet, set_id)
        if pin_set is None:
            raise HTTPException(status_code=404, detail="Pin set not found")
        _assert_can_edit_set(pin_set, current_user)

        results: list[Pin] = []
        if q.strip():
            results = search_pin(query=q.strip(), session=db) or []
        existing_ids: set[int] = set(
            db.scalars(
                select(pin_set_memberships.c.pin_id).where(
                    pin_set_memberships.c.set_id == set_id
                )
            ).all()
        )

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
