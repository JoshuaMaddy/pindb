from datetime import datetime, timezone
from typing import Any, Literal, cast

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.auth import require_admin
from pindb.database import Artist, Material, Pin, PinSet, Shop, Tag, session_maker
from pindb.database.audit_mixin import AuditMixin
from pindb.database.pending_mixin import PendingAuditEntity, PendingMixin
from pindb.database.user import User
from pindb.templates.admin.pending import pending_page

router = APIRouter(prefix="/admin/pending", dependencies=[Depends(require_admin)])

EntityType = Literal["pin", "shop", "artist", "tag", "material", "pin_set"]

_ENTITY_MAP: dict[str, type] = {
    "pin": Pin,
    "shop": Shop,
    "artist": Artist,
    "tag": Tag,
    "material": Material,
    "pin_set": PinSet,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_pending_entity(
    session: Session,
    entity_type: EntityType,
    entity_id: int,
) -> PendingAuditEntity:
    """Fetch a pending entity by type + id, bypassing pending filter."""
    model = _ENTITY_MAP.get(entity_type)
    if model is None:
        raise HTTPException(status_code=404, detail="Unknown entity type")

    pending_opts: Any = {"include_pending": True}
    raw = session.get(model, entity_id, execution_options=pending_opts)
    if raw is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return cast(PendingAuditEntity, raw)


def _approve_entity(
    entity: PendingAuditEntity, user_id: int | None, now: datetime
) -> None:
    """Set approved_at on entity; skip if already approved."""
    if entity.approved_at is not None:
        return
    entity.approved_at = now  # type: ignore[misc]
    entity.approved_by_id = user_id  # type: ignore[misc]


def _approve_with_cascade(
    entity: PendingAuditEntity, user_id: int | None, now: datetime
) -> None:
    """Approve entity and any pending direct dependencies (Pin only)."""
    _approve_entity(entity, user_id, now)

    if not isinstance(entity, Pin):
        return

    for rel in [*entity.shops, *entity.artists, *entity.materials, *entity.tags]:
        if (
            isinstance(rel, PendingMixin)
            and rel.approved_at is None
            and rel.rejected_at is None
        ):
            _approve_entity(rel, user_id, now)  # type: ignore[arg-type]


@router.get("")
def get_pending_queue(request: Request) -> HTMLResponse:
    with session_maker() as session:
        opts: dict[str, bool] = {"include_pending": True}

        pending_pins = session.scalars(
            select(Pin)
            .where(
                Pin.approved_at.is_(None),
                Pin.rejected_at.is_(None),
                Pin.deleted_at.is_(None),
            )
            .options(
                selectinload(Pin.shops),
                selectinload(Pin.artists),
                selectinload(Pin.materials),
                selectinload(Pin.tags),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()
        pending_shops = session.scalars(
            select(Shop)
            .where(
                Shop.approved_at.is_(None),
                Shop.rejected_at.is_(None),
                Shop.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()
        pending_artists = session.scalars(
            select(Artist)
            .where(
                Artist.approved_at.is_(None),
                Artist.rejected_at.is_(None),
                Artist.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()
        pending_tags = session.scalars(
            select(Tag)
            .where(
                Tag.approved_at.is_(None),
                Tag.rejected_at.is_(None),
                Tag.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()
        pending_materials = session.scalars(
            select(Material)
            .where(
                Material.approved_at.is_(None),
                Material.rejected_at.is_(None),
                Material.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()
        pending_pin_sets = session.scalars(
            select(PinSet)
            .where(
                PinSet.approved_at.is_(None),
                PinSet.rejected_at.is_(None),
                PinSet.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()

        creator_ids = {
            e.created_by_id
            for group in [
                pending_pins,
                pending_shops,
                pending_artists,
                pending_tags,
                pending_materials,
                pending_pin_sets,
            ]
            for e in group
            if e.created_by_id is not None
        }
        creators: dict[int, User] = {}
        if creator_ids:
            creators = {
                u.id: u
                for u in session.scalars(
                    select(User).where(User.id.in_(creator_ids))
                ).all()
            }

        return HTMLResponse(
            content=str(
                pending_page(
                    request=request,
                    pending_pins=list(pending_pins),
                    pending_shops=list(pending_shops),
                    pending_artists=list(pending_artists),
                    pending_tags=list(pending_tags),
                    pending_materials=list(pending_materials),
                    pending_pin_sets=list(pending_pin_sets),
                    creators=creators,
                )
            )
        )


@router.post("/approve/{entity_type}/{entity_id}")
def approve_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)

        if entity_type == "pin":
            pin_with_rels = session.scalar(
                select(Pin)
                .where(Pin.id == entity_id)
                .options(
                    selectinload(Pin.shops),
                    selectinload(Pin.artists),
                    selectinload(Pin.materials),
                    selectinload(Pin.tags),
                )
                .execution_options(include_pending=True)  # type: ignore[call-overload]
            )
            if pin_with_rels is not None:
                entity = pin_with_rels  # type: ignore[assignment]

        _approve_with_cascade(entity, current_user.id, now)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/reject/{entity_type}/{entity_id}")
def reject_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)
        if entity.rejected_at is None:
            entity.rejected_at = now  # type: ignore[misc]
            entity.rejected_by_id = current_user.id  # type: ignore[misc]

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/delete/{entity_type}/{entity_id}")
def delete_pending_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)
        if isinstance(entity, AuditMixin):
            entity.deleted_at = now
            entity.deleted_by_id = current_user.id

    return RedirectResponse(url="/admin/pending", status_code=303)
