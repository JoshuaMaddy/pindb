import logging
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.audit_events import get_audit_user
from pindb.auth import require_admin
from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.search.update import delete_pin as delete_pin_from_index

router = APIRouter(prefix="/delete", dependencies=[Depends(require_admin)])

LOGGER = logging.getLogger("pindb.routes.delete")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get(path="/pin/{id}")
def post_delete_pin(id: int) -> RedirectResponse:
    now = _utc_now()
    user_id = get_audit_user()
    with session_maker.begin() as session:
        pin: Pin | None = session.scalar(statement=select(Pin).where(Pin.id == id))
        if pin is not None:
            pin.deleted_at = now
            pin.deleted_by_id = user_id

    delete_pin_from_index(pin_id=id)
    return RedirectResponse(url="/", status_code=303)


@router.get(path="/artist/{id}")
def post_delete_artist(id: int) -> RedirectResponse:
    now = _utc_now()
    user_id = get_audit_user()
    with session_maker.begin() as session:
        artist: Artist | None = session.scalar(
            statement=select(Artist).where(Artist.id == id)
        )
        if artist is not None:
            artist.deleted_at = now
            artist.deleted_by_id = user_id

    return RedirectResponse(url="/", status_code=303)


@router.post(path="/tag/{id}")
def post_delete_tag(id: int) -> RedirectResponse:
    now = _utc_now()
    user_id = get_audit_user()
    with session_maker.begin() as session:
        tag: Tag | None = session.scalar(statement=select(Tag).where(Tag.id == id))
        if tag is not None:
            tag.deleted_at = now
            tag.deleted_by_id = user_id

    return RedirectResponse(url="/", status_code=303)


@router.post(path="/shop/{id}")
def post_delete_shop(id: int) -> RedirectResponse:
    now = _utc_now()
    user_id = get_audit_user()
    with session_maker.begin() as session:
        shop: Shop | None = session.scalar(statement=select(Shop).where(Shop.id == id))
        if shop is not None:
            shop.deleted_at = now
            shop.deleted_by_id = user_id

    return RedirectResponse(url="/", status_code=303)
