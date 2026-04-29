"""
FastAPI routes: `routes/get/tag.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.auth import CurrentUser
from pindb.database import Pin, Tag, session_maker
from pindb.database.joins import pins_tags
from pindb.database.pending_edit_utils import maybe_apply_pending_view
from pindb.database.tag import resolve_implications
from pindb.routes._urls import canonical_slug_redirect, slugify_for_url, tag_url
from pindb.search.search import search_entity_options
from pindb.search.update import TAGS_INDEX
from pindb.templates.components.pins.paginated_pin_grid import (
    _SECTION_ID,
    paginated_pin_grid,
)
from pindb.templates.get.tag import (
    tag_implication_preview,
    tag_page,
    tag_relation_items,
)

router = APIRouter()

_PER_PAGE: int = 100


@router.get(path="/tag-options")
def get_tag_options(
    q: str = Query(default=""),
    exclude_id: int | None = Query(default=None),
) -> JSONResponse:
    results = search_entity_options(TAGS_INDEX, q)
    if exclude_id is not None:
        results = [r for r in results if r["value"] != str(exclude_id)]
    return JSONResponse(content=results)


@router.get(path="/tag-implication-preview")
def get_tag_implication_preview(
    tag_ids: list[int] = Query(default_factory=list),
) -> HTMLResponse:
    if not tag_ids:
        return HTMLResponse(content="")
    with session_maker() as session:
        selected = set(
            session.scalars(
                select(Tag)
                .where(Tag.id.in_(tag_ids))
                .options(selectinload(Tag.implications))
            ).all()
        )
        resolved = resolve_implications(selected, session)
    return HTMLResponse(
        content=str(tag_implication_preview(set(resolved.keys()), selected))
    )


@router.get(path="/tag/{id}/relations/{direction}", response_model=None)
def get_tag_relations(
    request: Request,
    id: int,
    direction: str,
) -> HTMLResponse:
    if direction not in ("implications", "implied_by"):
        return HTMLResponse("")
    with session_maker() as session:
        tag_obj: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(
                selectinload(Tag.implications),
                selectinload(Tag.implied_by),
            )
        )
        if not tag_obj:
            return HTMLResponse("")
        tags = list(getattr(tag_obj, direction))
    return HTMLResponse(
        content=str(tag_relation_items(tags, request, id, direction, collapsed=False))
    )


@router.get(path="/tag/{slug}/{id}", response_model=None, name="get_tag")
@router.get(
    path="/tag/{id}",
    response_model=None,
    name="get_tag_by_id",
    include_in_schema=False,
)
def get_tag(
    request: Request,
    id: int,
    current_user: CurrentUser,
    slug: str | None = None,
    page: int = Query(default=1, ge=1),
    version: str | None = Query(default=None),
) -> HTMLResponse | RedirectResponse:
    with session_maker() as session:
        tag_obj: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(
                selectinload(Tag.implications),
                selectinload(Tag.implied_by),
                selectinload(Tag.aliases),
            )
        )

        if not tag_obj:
            return RedirectResponse(url="/")

        canonical_slug: str = slugify_for_url(name=tag_obj.name, fallback="tag")
        if slug != canonical_slug:
            return canonical_slug_redirect(
                request=request,
                route_name="get_tag",
                canonical_slug=canonical_slug,
                id=id,
            )

        pending_chain_exists, viewing_pending = maybe_apply_pending_view(
            session=session,
            entity=tag_obj,
            entity_table="tags",
            current_user=current_user,
            version=version,
        )

        offset: int = (page - 1) * _PER_PAGE

        total_count: int = (
            session.scalar(
                select(func.count(Pin.id))
                .join(pins_tags, Pin.id == pins_tags.c.pin_id)
                .where(pins_tags.c.tag_id == tag_obj.id)
            )
            or 0
        )

        pins: Sequence[Pin] = session.scalars(
            select(Pin)
            .join(pins_tags, Pin.id == pins_tags.c.pin_id)
            .where(pins_tags.c.tag_id == tag_obj.id)
            .order_by(Pin.name.asc())
            .limit(_PER_PAGE)
            .offset(offset)
        ).all()

        if request.headers.get("HX-Target") == _SECTION_ID:
            return HTMLResponse(
                content=str(
                    paginated_pin_grid(
                        request=request,
                        pins=pins,
                        total_count=total_count,
                        page=page,
                        page_url=str(tag_url(request=request, tag=tag_obj)),
                        per_page=_PER_PAGE,
                    )
                )
            )

        return HTMLResponse(
            content=str(
                tag_page(
                    request=request,
                    tag=tag_obj,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    per_page=_PER_PAGE,
                    has_pending_chain=pending_chain_exists,
                    viewing_pending=viewing_pending,
                )
            )
        )
