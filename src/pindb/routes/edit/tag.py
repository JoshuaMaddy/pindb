"""
FastAPI routes: `routes/edit/tag.py`.
"""

from typing import Sequence

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Tag, TagCategory, session_maker
from pindb.database.joins import pins_tags
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.database.tag import (
    _cascade_remove_implied,
    normalize_tag_name,
    replace_tag_aliases,
    resolve_implications,
)
from pindb.htmx_toast import hx_redirect_with_toast_headers
from pindb.log import user_logger
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes.edit._pending_helpers import submit_pending_edit
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.edit.tag")


@router.get(path="/tag/{id}", response_model=None)
def get_edit_tag(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    with session_maker() as session:
        tag: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
        )

        if tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")

        assert_editor_can_edit(tag, current_user)

        if needs_pending_edit(tag, current_user):
            chain = get_edit_chain(session, "tags", id)
            if chain:
                effective = get_effective_snapshot(tag, chain)
                with session.no_autoflush:
                    apply_snapshot_in_memory(tag, effective, session)

        options_url = str(request.url_for("get_tag_options")) + f"?exclude_id={id}"

        return HTMLResponse(
            content=str(
                tag_form(
                    post_url=request.url_for("post_edit_tag", id=id),
                    tag=tag,
                    request=request,
                    options_url=options_url,
                )
            )
        )


@router.post(path="/tag/{id}", response_model=None)
def post_edit_tag(
    request: Request,
    id: int,
    current_user: EditorUser,
    name: str = Form(),
    description: str | None = Form(default=None),
    category: TagCategory = Form(default=TagCategory.general),
    implication_ids: list[int] = Form(default_factory=list),
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    with session_maker.begin() as session:
        tag: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
        )

        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        assert_editor_can_edit(tag, current_user)

        if needs_pending_edit(tag, current_user):
            LOGGER.info("Submitting pending edit for tag id=%d name=%r", id, name)
            return submit_pending_edit(
                session=session,
                entity=tag,
                entity_table="tags",
                entity_id=id,
                field_updates={
                    "name": normalize_tag_name(name),
                    "description": description or None,
                    "category": category.value,
                    "implication_ids": sorted(implication_ids),
                    "aliases": sorted(
                        normalize_tag_name(alias) for alias in aliases if alias.strip()
                    ),
                },
                current_user=current_user,
                request=request,
                redirect_route="get_tag",
            )

        LOGGER.info("Editing tag id=%d name=%r category=%s", id, name, category.value)
        tag.name = normalize_tag_name(name)
        tag.description = description or None
        tag.category = category

        old_implication_ids: set[int] = {
            implied_tag.id for implied_tag in tag.implications
        }
        implied_tags: Sequence[Tag] = session.scalars(
            select(Tag).where(Tag.id.in_(implication_ids))
        ).all()
        tag.implications = set(implied_tags)

        new_implication_ids: set[int] = {implied_tag.id for implied_tag in implied_tags}
        newly_added_ids: set[int] = new_implication_ids - old_implication_ids
        removed_ids: set[int] = old_implication_ids - new_implication_ids

        session.flush()  # write tag_implications changes before cascading

        if newly_added_ids:
            newly_added_tags: list[Tag] = [
                implied_tag
                for implied_tag in implied_tags
                if implied_tag.id in newly_added_ids
            ]
            all_new_implied: dict[Tag, Tag | None] = resolve_implications(
                initial=newly_added_tags,
                session=session,
            )

            for implied_tag, source_tag in all_new_implied.items():
                session.execute(
                    pg_insert(pins_tags)
                    .from_select(
                        ["pin_id", "tag_id", "implied_by_tag_id"],
                        select(
                            pins_tags.c.pin_id,
                            literal(implied_tag.id).label("tag_id"),
                            literal(source_tag.id if source_tag else None).label(
                                "implied_by_tag_id"
                            ),
                        ).where(pins_tags.c.tag_id == tag.id),
                    )
                    .on_conflict_do_nothing()
                )

        if removed_ids:
            _cascade_remove_implied(tag.id, removed_ids, session)

        replace_tag_aliases(tag=tag, aliases=aliases, session=session)

        session.flush()
        tag_id: int = tag.id

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(request.url_for("get_tag", id=tag_id)),
            message="Tag updated.",
        )
    )
