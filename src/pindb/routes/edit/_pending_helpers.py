from typing import Iterable

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from pindb.database.artist import Artist
from pindb.database.link import Link
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_edit_utils import (
    compute_patch,
    get_edit_chain,
    get_effective_snapshot,
    get_head_edit,
)
from pindb.database.pin import Pin
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User


def submit_pending_edit(
    *,
    session: Session,
    entity: Pin | Artist | Shop | Tag,
    entity_table: str,
    entity_id: int,
    field_updates: dict[str, object],
    current_user: User,
    request: Request,
    redirect_route: str,
) -> HTMLResponse:
    """Diff ``field_updates`` against the entity's current effective snapshot;
    if non-empty, persist a new PendingEdit row.

    Always returns the HTMLResponse the caller should hand back to the client:
    a plain HX-Redirect when there is nothing to save, or one with
    ``?version=pending`` when a new pending edit was queued.
    """
    chain = get_edit_chain(session, entity_table, entity_id)
    old_snapshot: dict[str, object] = get_effective_snapshot(entity, chain)

    new_snapshot: dict[str, object] = dict(old_snapshot)
    new_snapshot.update(field_updates)

    redirect_url = str(request.url_for(redirect_route, id=entity_id))

    patch = compute_patch(old_snapshot, new_snapshot)
    if not patch:
        return HTMLResponse(headers={"HX-Redirect": redirect_url})

    head = get_head_edit(session, entity_table, entity_id)
    session.add(
        PendingEdit(
            entity_type=entity_table,
            entity_id=entity_id,
            patch=patch,
            created_by_id=current_user.id,
            parent_id=head.id if head else None,
        )
    )

    return HTMLResponse(headers={"HX-Redirect": redirect_url + "?version=pending"})


def replace_links(
    *,
    entity: object,
    urls: Iterable[str] | None,
    session: Session,
) -> None:
    """Delete existing Link rows on ``entity`` and replace them with one per url.

    Caller must have selectinloaded ``entity.links``.
    """
    existing_links: list[Link] = list(getattr(entity, "links"))
    for old_link in existing_links:
        session.delete(old_link)

    new_links: set[Link] = {Link(url) for url in (urls or [])}
    setattr(entity, "links", new_links)
