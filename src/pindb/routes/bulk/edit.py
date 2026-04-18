"""Bulk edit flow.

Lets editors/admins apply a constrained set of field changes and tag
modifications to many pins at once. The source of the pin list is one of:

- a PinSet / Artist / Shop / Tag entity (editor allowed)
- a search query (admin only)

Editors on entity sources go through `submit_pending_edit()` per pin, with
every created `PendingEdit` sharing a single `bulk_id` so the admin
approval queue can group them. Admins bypass pending entirely; search
bulk edits always bypass pending and are admin-only.
"""

from __future__ import annotations

from typing import Annotated, Sequence
from uuid import UUID, uuid4

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import AdminUser, EditorUser
from pindb.database import session_maker
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_edit_utils import (
    compute_patch,
    get_effective_snapshot,
    get_edit_chain,
    get_head_edit,
)
from pindb.database.pin import Pin
from pindb.database.tag import Tag, apply_pin_tags
from pindb.routes.bulk._helpers import (
    BULK_SCALAR_FIELDS,
    BulkEditSource,
    TagMode,
    _coerce_bulk_scalar,
    apply_bulk_scalars,
    compute_tag_change,
    resolve_pin_ids,
    resolve_source_name,
    snapshot_scalar_updates,
    source_redirect_route,
)
from pindb.search.search import search_pin
from pindb.templates.bulk.edit import bulk_edit_page

router = APIRouter(prefix="/bulk-edit")


_PIN_SELECTINLOADS = (
    selectinload(Pin.shops),
    selectinload(Pin.tags),
    selectinload(Pin.explicit_tags),
    selectinload(Pin.artists),
    selectinload(Pin.sets),
    selectinload(Pin.links),
    selectinload(Pin.grades),
    selectinload(Pin.currency),
)


@router.get("/from/{source_type}/{source_id}", response_model=None)
def get_bulk_edit_entity(
    request: Request,
    source_type: BulkEditSource,
    source_id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    with session_maker() as session:
        pin_ids = resolve_pin_ids(session, source_type, source_id)
        source_name = resolve_source_name(session, source_type, source_id)
        tags: Sequence[Tag] = session.scalars(select(Tag)).all()

        options_base_url: str = str(
            request.url_for("get_entity_options", entity_type="placeholder")
        ).removesuffix("/placeholder")

        post_url = str(request.url_for("post_bulk_edit_apply")) + (
            f"?source_type={source_type.value}&source_id={source_id}"
        )

        return HTMLResponse(
            content=str(
                bulk_edit_page(
                    post_url=post_url,
                    source_label=f"{source_type.value.replace('_', ' ').title()}: {source_name}",
                    source_description=(
                        f"Apply changes to every pin in this "
                        f"{source_type.value.replace('_', ' ')}."
                    ),
                    pin_count=len(pin_ids),
                    tags=tags,
                    options_base_url=options_base_url,
                    viewer_is_admin=current_user.is_admin,
                    request=request,
                )
            )
        )


@router.get("/from/search", response_model=None)
def get_bulk_edit_search(
    request: Request,
    current_user: AdminUser,
    q: str = "",
) -> HTMLResponse:
    with session_maker() as session:
        pins = search_pin(query=q, session=session) or []
        pin_count = len(pins)
        tags: Sequence[Tag] = session.scalars(select(Tag)).all()

        options_base_url: str = str(
            request.url_for("get_entity_options", entity_type="placeholder")
        ).removesuffix("/placeholder")

        post_url = str(request.url_for("post_bulk_edit_apply")) + f"?search_query={q}"

        return HTMLResponse(
            content=str(
                bulk_edit_page(
                    post_url=post_url,
                    source_label=f"Search: {q!r}",
                    source_description="Apply changes to every pin matching this search.",
                    pin_count=pin_count,
                    tags=tags,
                    options_base_url=options_base_url,
                    viewer_is_admin=current_user.is_admin,
                    request=request,
                )
            )
        )


@router.post("/apply", response_model=None)
def post_bulk_edit_apply(
    request: Request,
    current_user: EditorUser,
    source_type: BulkEditSource | None = None,
    source_id: int | None = None,
    search_query: str | None = None,
    apply_field: Annotated[list[str], Form(default_factory=list)] = [],
    tag_ids: Annotated[list[int], Form(default_factory=list)] = [],
    tag_mode: TagMode = Form(default=TagMode.add),
    acquisition_type_value: str | None = Form(default=None),
    funding_type_value: str | None = Form(default=None),
    limited_edition_value: str | None = Form(default=None),
    number_produced_value: str | None = Form(default=None),
    posts_value: str | None = Form(default=None),
    width_value: str | None = Form(default=None),
    height_value: str | None = Form(default=None),
    release_date_value: str | None = Form(default=None),
    end_date_value: str | None = Form(default=None),
) -> RedirectResponse | HTMLResponse:
    if search_query is not None:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Bulk editing search results is admin-only."
            )
        use_pending_flow = False
        redirect_url = str(request.url_for("get_search_pin"))
    else:
        if source_type is None or source_id is None:
            raise HTTPException(
                status_code=400, detail="Missing source_type / source_id."
            )
        use_pending_flow = not current_user.is_admin
        redirect_url = str(
            request.url_for(source_redirect_route(source_type), id=source_id)
        )

    submitted_field_values: dict[str, object] = {
        "acquisition_type": acquisition_type_value,
        "funding_type": funding_type_value,
        "limited_edition": limited_edition_value,
        "number_produced": number_produced_value,
        "posts": posts_value,
        "width": width_value,
        "height": height_value,
        "release_date": release_date_value,
        "end_date": end_date_value,
    }
    # Only keep fields the user ticked — coerce to the target type here so
    # downstream writers and snapshotters all see the same typed value.
    field_updates: dict[str, object] = {
        field: _coerce_bulk_scalar(field, submitted_field_values[field])
        for field in BULK_SCALAR_FIELDS
        if field in apply_field and field in submitted_field_values
    }

    tag_change_requested: bool = bool(tag_ids) or tag_mode == TagMode.replace

    if not field_updates and not tag_change_requested:
        return RedirectResponse(url=redirect_url, status_code=303)

    bulk_id: UUID = uuid4()
    submitted_tags: set[int] = set(tag_ids)

    with session_maker.begin() as session:
        if search_query is not None:
            pins_found = search_pin(query=search_query, session=session) or []
            pin_id_list: list[int] = [pin.id for pin in pins_found]
        else:
            assert source_type is not None and source_id is not None
            pin_id_list = resolve_pin_ids(session, source_type, source_id)

        if not pin_id_list:
            return RedirectResponse(url=redirect_url, status_code=303)

        pins: list[Pin] = list(
            session.scalars(
                select(Pin).where(Pin.id.in_(pin_id_list)).options(*_PIN_SELECTINLOADS)
            ).all()
        )

        for pin in pins:
            _apply_to_pin(
                session=session,
                pin=pin,
                field_updates=field_updates,
                tag_change_requested=tag_change_requested,
                submitted_tags=submitted_tags,
                tag_mode=tag_mode,
                use_pending_flow=use_pending_flow,
                current_user_id=current_user.id,
                bulk_id=bulk_id,
            )

    return RedirectResponse(url=redirect_url + f"?bulk={bulk_id}", status_code=303)


def _apply_to_pin(
    *,
    session,
    pin: Pin,
    field_updates: dict[str, object],
    tag_change_requested: bool,
    submitted_tags: set[int],
    tag_mode: TagMode,
    use_pending_flow: bool,
    current_user_id: int | None,
    bulk_id: UUID,
) -> None:
    current_tag_ids: set[int] = {tag.id for tag in pin.explicit_tags}
    new_tag_ids: set[int] = (
        compute_tag_change(current_tag_ids, submitted_tags, tag_mode)
        if tag_change_requested
        else current_tag_ids
    )

    if use_pending_flow:
        chain = get_edit_chain(session, "pins", pin.id)
        old_snapshot = get_effective_snapshot(pin, chain)
        new_snapshot = dict(old_snapshot)
        new_snapshot.update(snapshot_scalar_updates(field_updates))
        if tag_change_requested:
            new_snapshot["tag_ids"] = sorted(new_tag_ids)
        patch = compute_patch(old_snapshot, new_snapshot)
        if not patch:
            return
        head = get_head_edit(session, "pins", pin.id)
        session.add(
            PendingEdit(
                entity_type="pins",
                entity_id=pin.id,
                patch=patch,
                created_by_id=current_user_id,
                parent_id=head.id if head else None,
                bulk_id=bulk_id,
            )
        )
        return

    # Direct write path (admin or search source).
    apply_bulk_scalars(pin, field_updates)
    if tag_change_requested and new_tag_ids != current_tag_ids:
        apply_pin_tags(pin.id, new_tag_ids, session)
