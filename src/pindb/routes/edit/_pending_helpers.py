"""
FastAPI routes: `routes/edit/_pending_helpers.py`.
"""

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
from pindb.htmx_toast import hx_redirect_with_toast_headers
from pindb.routes._urls import slugify_for_url


async def submit_pending_edit(
    *,
    session: AsyncSession,
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
    chain = await get_edit_chain(session, entity_table, entity_id)
    old_snapshot: dict[str, object] = get_effective_snapshot(entity, chain)

    new_snapshot: dict[str, object] = dict(old_snapshot)
    new_snapshot.update(field_updates)

    canonical_slug: str = slugify_for_url(
        name=getattr(entity, "name", ""), fallback=entity_table.rstrip("s") or "entity"
    )
    redirect_url = str(
        request.url_for(redirect_route, slug=canonical_slug, id=entity_id)
    )

    patch = compute_patch(old_snapshot, new_snapshot)
    if not patch:
        return HTMLResponse(
            headers=hx_redirect_with_toast_headers(
                redirect_url=redirect_url,
                message="No changes to save.",
            )
        )

    head = await get_head_edit(session, entity_table, entity_id)
    session.add(
        PendingEdit(
            entity_type=entity_table,
            entity_id=entity_id,
            patch=patch,
            created_by_id=current_user.id,
            parent_id=head.id if head else None,
        )
    )

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=redirect_url + "?version=pending",
            message="Changes submitted for review.",
        )
    )


async def replace_links(
    *,
    entity: object,
    urls: Iterable[str] | None,
    session: AsyncSession,
) -> None:
    """Delete existing Link rows on ``entity`` and replace them with one per url.

    Caller must have selectinloaded ``entity.links``.
    """
    existing_links: list[Link] = list(getattr(entity, "links"))
    for old_link in existing_links:
        await session.delete(old_link)

    new_links: set[Link] = {Link(url) for url in (urls or [])}
    setattr(entity, "links", new_links)


async def submit_simple_aliased_pending_edit(
    *,
    session: AsyncSession,
    entity: Artist | Shop,
    entity_table: str,
    entity_id: int,
    name: str,
    description: str | None,
    links: list[str] | None,
    aliases: list[str],
    current_user: User,
    request: Request,
    redirect_route: str,
) -> HTMLResponse:
    """Pending-edit submission for entities with name/description/links/aliases."""
    return await submit_pending_edit(
        session=session,
        entity=entity,
        entity_table=entity_table,
        entity_id=entity_id,
        field_updates={
            "name": name,
            "description": description,
            "links": sorted(links or []),
            "aliases": sorted(alias for alias in aliases if alias.strip()),
        },
        current_user=current_user,
        request=request,
        redirect_route=redirect_route,
    )


async def apply_simple_aliased_direct_edit(
    *,
    entity: Artist | Shop,
    name: str,
    description: str | None,
    links: list[str] | None,
    aliases: list[str],
    replace_aliases_fn: Callable[[Any, Iterable[str], AsyncSession], Awaitable[None]],
    session: AsyncSession,
) -> None:
    """In-place write for name/description/links/aliases (admin path)."""
    entity.name = name
    entity.description = description
    await replace_links(entity=entity, urls=links, session=session)
    await replace_aliases_fn(entity, aliases, session)
