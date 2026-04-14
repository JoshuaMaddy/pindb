from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.auth import CurrentUser
from pindb.database import Pin, Tag, session_maker
from pindb.database.joins import pins_tags
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
    has_pending_edits,
)
from pindb.database.tag import resolve_implications
from pindb.templates.components.paginated_pin_grid import (
    _SECTION_ID,
    paginated_pin_grid,
)
from pindb.templates.get.tag import tag_implication_preview, tag_page

router = APIRouter()

_PER_PAGE: int = 100


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
    return HTMLResponse(content=str(tag_implication_preview(resolved, selected)))


@router.get(path="/tag/{id}", response_model=None)
def get_tag(
    request: Request,
    id: int,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    version: str | None = Query(default=None),
) -> HTMLResponse | RedirectResponse:
    can_see_pending = current_user is not None and (
        current_user.is_editor or current_user.is_admin
    )
    viewing_pending: bool = version == "pending" and can_see_pending

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

        pending_chain_exists: bool = can_see_pending and has_pending_edits(
            session, "tags", id
        )

        if viewing_pending and pending_chain_exists:
            chain = get_edit_chain(session, "tags", id)
            effective = get_effective_snapshot(tag_obj, chain)
            with session.no_autoflush:
                apply_snapshot_in_memory(tag_obj, effective, session)

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
                        page_url=str(request.url_for("get_tag", id=id)),
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
