from datetime import datetime, timezone
from typing import Any, cast

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.auth import require_admin
from pindb.database import Artist, Pin, PinSet, Shop, Tag, session_maker
from pindb.database.audit_mixin import AuditMixin
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_edit_utils import (
    apply_snapshot_to_entity,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.database.pending_mixin import PendingAuditEntity, PendingMixin
from pindb.database.user import User
from pindb.templates.admin.pending import pending_page

router = APIRouter(prefix="/admin/pending", dependencies=[Depends(require_admin)])


_ENTITY_TYPE_TO_TABLE: dict[EntityType, str] = {
    EntityType.pin: "pins",
    EntityType.shop: "shops",
    EntityType.artist: "artists",
    EntityType.tag: "tags",
    EntityType.pin_set: "pin_sets",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_pending_entity(
    session: Session,
    entity_type: EntityType,
    entity_id: int,
) -> PendingAuditEntity:
    """Fetch a pending entity by type + id, bypassing pending filter."""
    pending_opts: Any = {"include_pending": True}
    raw = session.get(entity_type.model, entity_id, execution_options=pending_opts)
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

    for rel in [*entity.shops, *entity.artists, *entity.tags]:
        if (
            isinstance(rel, PendingMixin)
            and rel.approved_at is None
            and rel.rejected_at is None
        ):
            _approve_entity(rel, user_id, now)  # type: ignore[arg-type]


def _load_pin_for_edit(session: Session, pin_id: int) -> Pin | None:
    return session.scalar(
        select(Pin)
        .where(Pin.id == pin_id)
        .options(
            selectinload(Pin.shops),
            selectinload(Pin.artists),
            selectinload(Pin.tags),
            selectinload(Pin.sets),
            selectinload(Pin.links),
            selectinload(Pin.grades),
            selectinload(Pin.currency),
        )
        .execution_options(include_pending=True)  # type: ignore[call-overload]
    )


def _load_entity_for_edit(
    session: Session, entity_type: EntityType, entity_id: int
) -> Pin | Shop | Artist | Tag | None:
    if entity_type == EntityType.pin:
        return _load_pin_for_edit(session, entity_id)
    if entity_type == EntityType.shop:
        return session.scalar(
            select(Shop)
            .where(Shop.id == entity_id)
            .options(selectinload(Shop.links))
            .execution_options(include_pending=True)  # type: ignore[call-overload]
        )
    if entity_type == EntityType.artist:
        return session.scalar(
            select(Artist)
            .where(Artist.id == entity_id)
            .options(selectinload(Artist.links))
            .execution_options(include_pending=True)  # type: ignore[call-overload]
        )
    if entity_type == EntityType.tag:
        return session.scalar(
            select(Tag)
            .where(Tag.id == entity_id)
            .options(
                selectinload(Tag.implications),
                selectinload(Tag.aliases),
            )
            .execution_options(include_pending=True)  # type: ignore[call-overload]
        )
    return None


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
        pending_pin_sets = session.scalars(
            select(PinSet)
            .where(
                PinSet.approved_at.is_(None),
                PinSet.rejected_at.is_(None),
                PinSet.deleted_at.is_(None),
            )
            .execution_options(**opts)  # type: ignore[arg-type]
        ).all()

        creator_ids: set[int] = {
            e.created_by_id
            for group in [
                pending_pins,
                pending_shops,
                pending_artists,
                pending_tags,
                pending_pin_sets,
            ]
            for e in group
            if e.created_by_id is not None
        }

        # Pending edits: group by (entity_type, entity_id)
        pending_edits = session.scalars(
            select(PendingEdit)
            .where(
                PendingEdit.approved_at.is_(None),
                PendingEdit.rejected_at.is_(None),
            )
            .order_by(PendingEdit.created_at.asc(), PendingEdit.id.asc())
        ).all()

        edit_groups: dict[tuple[str, int], list[PendingEdit]] = {}
        for edit in pending_edits:
            edit_groups.setdefault((edit.entity_type, edit.entity_id), []).append(edit)

        for edit in pending_edits:
            if edit.created_by_id is not None:
                creator_ids.add(edit.created_by_id)

        # Resolve entity names for each edit group
        group_entities: dict[tuple[str, int], PendingAuditEntity] = {}
        pending_opts: Any = {"include_pending": True}
        for (table_name, entity_id), _edits in edit_groups.items():
            et = _table_to_entity_type(table_name)
            if et is None:
                continue
            obj = session.get(et.model, entity_id, execution_options=pending_opts)
            if obj is not None:
                group_entities[(table_name, entity_id)] = cast(PendingAuditEntity, obj)

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
                    pending_pin_sets=list(pending_pin_sets),
                    creators=creators,
                    edit_groups=edit_groups,
                    edit_group_entities=group_entities,
                )
            )
        )


def _table_to_entity_type(table_name: str) -> EntityType | None:
    for et, tn in _ENTITY_TYPE_TO_TABLE.items():
        if tn == table_name:
            return et
    return None


@router.post("/approve/{entity_type}/{entity_id}")
def approve_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)

        if entity_type == EntityType.pin:
            pin_with_rels = session.scalar(
                select(Pin)
                .where(Pin.id == entity_id)
                .options(
                    selectinload(Pin.shops),
                    selectinload(Pin.artists),
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


# ---------------------------------------------------------------------------
# Pending edit chain approval
# ---------------------------------------------------------------------------


@router.post("/approve-edits/{entity_type}/{entity_id}")
def approve_pending_edits(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    table_name = _ENTITY_TYPE_TO_TABLE[entity_type]
    with session_maker.begin() as session:
        entity = _load_entity_for_edit(session, entity_type, entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")

        chain = get_edit_chain(session, table_name, entity_id)
        if not chain:
            return RedirectResponse(url="/admin/pending", status_code=303)

        effective = get_effective_snapshot(entity, chain)
        apply_snapshot_to_entity(entity, effective, session)

        for edit in chain:
            edit.approved_at = now
            edit.approved_by_id = current_user.id

        # Cascade pending deps when approving a pin edit (same as pin approval)
        if isinstance(entity, Pin):
            _approve_with_cascade(
                cast(PendingAuditEntity, entity), current_user.id, now
            )

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/reject-edits/{entity_type}/{entity_id}")
def reject_pending_edits(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = _utc_now()
    table_name = _ENTITY_TYPE_TO_TABLE[entity_type]
    with session_maker.begin() as session:
        chain = get_edit_chain(session, table_name, entity_id)
        for edit in chain:
            edit.rejected_at = now
            edit.rejected_by_id = current_user.id

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/delete-edits/{entity_type}/{entity_id}")
def delete_pending_edits(
    entity_type: EntityType,
    entity_id: int,
) -> RedirectResponse:
    table_name = _ENTITY_TYPE_TO_TABLE[entity_type]
    with session_maker.begin() as session:
        chain = get_edit_chain(session, table_name, entity_id)
        for edit in chain:
            session.delete(edit)

    return RedirectResponse(url="/admin/pending", status_code=303)
