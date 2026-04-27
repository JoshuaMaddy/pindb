"""
FastAPI routes: `routes/approve.py`.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

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
from pindb.search.update import delete_one, sync_entity, sync_pin_with_deps
from pindb.templates.admin.pending import BulkGroupView, pending_page
from pindb.utils import utc_now

router = APIRouter(prefix="/admin/pending", dependencies=[Depends(require_admin)])

_MODEL_TO_ENTITY_TYPE: dict[type, EntityType] = {et.model: et for et in EntityType}


def _entity_type_of(entity: object) -> EntityType | None:
    return _MODEL_TO_ENTITY_TYPE.get(type(entity))


class _BulkGroupBucket:
    """Staging container for a bulk_id's pending entities and edits."""

    def __init__(self) -> None:
        self.entities: list[tuple[str, PendingAuditEntity]] = []
        self.edits: list[tuple[tuple[str, int], list[PendingEdit]]] = []


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

        pending_pins_list: list[Pin] = list(pending_pins)
        pending_shops_list: list[Shop] = list(pending_shops)
        pending_artists_list: list[Artist] = list(pending_artists)
        pending_tags_list: list[Tag] = list(pending_tags)
        pending_pin_sets_list: list[PinSet] = list(pending_pin_sets)

        creator_ids: set[int] = {
            e.created_by_id
            for group in [
                pending_pins_list,
                pending_shops_list,
                pending_artists_list,
                pending_tags_list,
                pending_pin_sets_list,
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

        # Bulk groups: collect pending entities and edits keyed by bulk_id.
        # Any row with a bulk_id is pulled out of the flat per-type sections
        # and rendered as a single collapsible bundle.
        bulk_groups: dict[UUID, _BulkGroupBucket] = {}
        per_type_lists: list[tuple[list[PendingAuditEntity], str]] = [
            (cast(list[PendingAuditEntity], pending_pins_list), "pin"),
            (cast(list[PendingAuditEntity], pending_shops_list), "shop"),
            (cast(list[PendingAuditEntity], pending_artists_list), "artist"),
            (cast(list[PendingAuditEntity], pending_tags_list), "tag"),
            (cast(list[PendingAuditEntity], pending_pin_sets_list), "pin_set"),
        ]
        for pending_list, entity_type_slug in per_type_lists:
            for entity in list(pending_list):
                entity_bulk_id: UUID | None = getattr(entity, "bulk_id", None)
                if entity_bulk_id is None:
                    continue
                bucket = bulk_groups.setdefault(entity_bulk_id, _BulkGroupBucket())
                bucket.entities.append((entity_type_slug, entity))
                pending_list.remove(entity)

        for (table_name, entity_id), chain in list(edit_groups.items()):
            bulk_ids_in_chain = {edit.bulk_id for edit in chain if edit.bulk_id}
            if not bulk_ids_in_chain:
                continue
            # An entity's chain belongs to a bulk only if every pending edit on
            # it shares the bulk_id. Otherwise leave it in the per-entity list.
            if len(bulk_ids_in_chain) != 1 or any(
                edit.bulk_id is None for edit in chain
            ):
                continue
            bulk_id_val = next(iter(bulk_ids_in_chain))
            bucket = bulk_groups.setdefault(bulk_id_val, _BulkGroupBucket())
            bucket.edits.append(((table_name, entity_id), chain))
            edit_groups.pop((table_name, entity_id))

        for edit in pending_edits:
            if edit.created_by_id is not None:
                creator_ids.add(edit.created_by_id)

        # Resolve entity names for each edit group
        group_entities: dict[tuple[str, int], PendingAuditEntity] = {}
        pending_opts: Any = {"include_pending": True}
        for (table_name, entity_id), _edits in edit_groups.items():
            entity_type = EntityType.from_table_name(table_name)
            if entity_type is None:
                continue
            entity = session.get(
                entity_type.model, entity_id, execution_options=pending_opts
            )
            if entity is not None:
                group_entities[(table_name, entity_id)] = cast(
                    PendingAuditEntity, entity
                )

        creators: dict[int, User] = {}
        if creator_ids:
            creators = {
                u.id: u
                for u in session.scalars(
                    select(User).where(User.id.in_(creator_ids))
                ).all()
            }

        bulk_view_groups: list[BulkGroupView] = [
            BulkGroupView(
                bulk_id=bulk_id_val,
                entities=bucket.entities,
                edits=bucket.edits,
                edit_entities={
                    (table_name, entity_id): group_entities[(table_name, entity_id)]
                    for ((table_name, entity_id), _chain) in bucket.edits
                    if (table_name, entity_id) in group_entities
                },
            )
            for bulk_id_val, bucket in bulk_groups.items()
        ]

        return HTMLResponse(
            content=str(
                pending_page(
                    request=request,
                    pending_pins=pending_pins_list,
                    pending_shops=pending_shops_list,
                    pending_artists=pending_artists_list,
                    pending_tags=pending_tags_list,
                    pending_pin_sets=pending_pin_sets_list,
                    creators=creators,
                    edit_groups=edit_groups,
                    edit_group_entities=group_entities,
                    bulk_groups=bulk_view_groups,
                )
            )
        )


@router.post("/approve/{entity_type}/{entity_id}")
def approve_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
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

    if entity_type == EntityType.pin:
        sync_pin_with_deps(entity_id)
    else:
        sync_entity(entity_type, entity_id)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/reject/{entity_type}/{entity_id}")
def reject_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)
        if entity.rejected_at is None:
            entity.rejected_at = now  # type: ignore[misc]
            entity.rejected_by_id = current_user.id  # type: ignore[misc]

    delete_one(entity_type, entity_id)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/delete/{entity_type}/{entity_id}")
def delete_pending_entity(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    with session_maker.begin() as session:
        entity = _get_pending_entity(session, entity_type, entity_id)
        if isinstance(entity, AuditMixin):
            entity.deleted_at = now
            entity.deleted_by_id = current_user.id

    delete_one(entity_type, entity_id)

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
    now = utc_now()
    table_name = entity_type.table_name
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

    if entity_type == EntityType.pin:
        sync_pin_with_deps(entity_id)
    else:
        sync_entity(entity_type, entity_id)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/reject-edits/{entity_type}/{entity_id}")
def reject_pending_edits(
    entity_type: EntityType,
    entity_id: int,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    table_name = entity_type.table_name
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
    table_name = entity_type.table_name
    with session_maker.begin() as session:
        chain = get_edit_chain(session, table_name, entity_id)
        for edit in chain:
            session.delete(edit)

    return RedirectResponse(url="/admin/pending", status_code=303)


# ---------------------------------------------------------------------------
# Bulk approval helpers — operate on every pending edit and every pending
# PendingMixin entity that shares a given ``bulk_id``.
# ---------------------------------------------------------------------------


def _collect_bulk_entities(session: Session, bulk_id: UUID) -> list[PendingAuditEntity]:
    opts: Any = {"include_pending": True}
    collected: list[PendingAuditEntity] = []
    for entity_type in EntityType:
        rows = session.scalars(
            select(entity_type.model)
            .where(entity_type.model.bulk_id == bulk_id)
            .execution_options(**opts)
        ).all()
        collected.extend(cast(list[PendingAuditEntity], list(rows)))
    return collected


def _collect_bulk_edits(session: Session, bulk_id: UUID) -> list[PendingEdit]:
    return list(
        session.scalars(
            select(PendingEdit).where(
                PendingEdit.bulk_id == bulk_id,
                PendingEdit.approved_at.is_(None),
                PendingEdit.rejected_at.is_(None),
            )
        ).all()
    )


@router.post("/approve-bulk/{bulk_id}")
def approve_bulk(
    bulk_id: UUID,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    to_sync: set[tuple[EntityType, int]] = set()

    with session_maker.begin() as session:
        for entity in _collect_bulk_entities(session, bulk_id):
            if entity.approved_at is None and entity.rejected_at is None:
                _approve_with_cascade(entity, current_user.id, now)
                et = _entity_type_of(entity)
                if et is not None:
                    to_sync.add((et, entity.id))

        edits = _collect_bulk_edits(session, bulk_id)
        edits_by_entity: dict[tuple[str, int], list[PendingEdit]] = {}
        for edit in edits:
            edits_by_entity.setdefault((edit.entity_type, edit.entity_id), []).append(
                edit
            )

        for (table_name, entity_id), chain in edits_by_entity.items():
            entity_type = EntityType.from_table_name(table_name)
            if entity_type is None:
                continue
            canonical = _load_entity_for_edit(session, entity_type, entity_id)
            if canonical is None:
                continue
            # Apply the full effective chain, not just the bulk slice, so other
            # pending edits that happened to stack on top are preserved.
            full_chain = get_edit_chain(session, table_name, entity_id)
            effective = get_effective_snapshot(canonical, full_chain)
            apply_snapshot_to_entity(canonical, effective, session)
            for edit in full_chain:
                edit.approved_at = now
                edit.approved_by_id = current_user.id
            to_sync.add((entity_type, entity_id))

    for et, eid in to_sync:
        if et == EntityType.pin:
            sync_pin_with_deps(eid)
        else:
            sync_entity(et, eid)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/reject-bulk/{bulk_id}")
def reject_bulk(
    bulk_id: UUID,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    to_delete: list[tuple[EntityType, int]] = []

    with session_maker.begin() as session:
        for entity in _collect_bulk_entities(session, bulk_id):
            if entity.rejected_at is None and entity.approved_at is None:
                entity.rejected_at = now  # type: ignore[misc]
                entity.rejected_by_id = current_user.id  # type: ignore[misc]
                et = _entity_type_of(entity)
                if et is not None:
                    to_delete.append((et, entity.id))

        for edit in _collect_bulk_edits(session, bulk_id):
            edit.rejected_at = now
            edit.rejected_by_id = current_user.id

    for et, eid in to_delete:
        delete_one(et, eid)

    return RedirectResponse(url="/admin/pending", status_code=303)


@router.post("/delete-bulk/{bulk_id}")
def delete_bulk(
    bulk_id: UUID,
    current_user: User = Depends(require_admin),
) -> RedirectResponse:
    now = utc_now()
    with session_maker.begin() as session:
        to_delete: list[tuple[EntityType, int]] = []
        for entity in _collect_bulk_entities(session, bulk_id):
            if isinstance(entity, AuditMixin) and entity.deleted_at is None:
                entity.deleted_at = now
                entity.deleted_by_id = current_user.id
                et = _entity_type_of(entity)
                if et is not None:
                    to_delete.append((et, entity.id))

        for edit in _collect_bulk_edits(session, bulk_id):
            session.delete(edit)

    for et, eid in to_delete:
        delete_one(et, eid)

    return RedirectResponse(url="/admin/pending", status_code=303)
