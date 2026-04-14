from typing import Any, Sequence

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Tag, TagAlias, TagCategory, session_maker
from pindb.database.joins import pins_tags
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    compute_patch,
    get_edit_chain,
    get_effective_snapshot,
    get_head_edit,
)
from pindb.database.tag import resolve_implications
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()


@router.get(path="/tag/{id}", response_model=None)
def get_edit_tag(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse | None:
    with session_maker() as session:
        tag: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
        )

        if tag is None:
            return None

        assert_editor_can_edit(tag, current_user)

        if needs_pending_edit(tag, current_user):
            chain = get_edit_chain(session, "tags", id)
            if chain:
                effective = get_effective_snapshot(tag, chain)
                with session.no_autoflush:
                    apply_snapshot_in_memory(tag, effective, session)

        all_tags: Sequence[Tag] = session.scalars(
            select(Tag).where(Tag.id != id).order_by(Tag.name.asc())
        ).all()

        return HTMLResponse(
            content=str(
                tag_form(
                    post_url=request.url_for("post_edit_tag", id=id),
                    tag=tag,
                    request=request,
                    all_tags=list(all_tags),
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
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        tag: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.id == id)
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
        )

        if not tag:
            return None

        assert_editor_can_edit(tag, current_user)

        if needs_pending_edit(tag, current_user):
            chain = get_edit_chain(session, "tags", id)
            old_snapshot: dict[str, Any] = get_effective_snapshot(tag, chain)

            new_snapshot: dict[str, Any] = dict(old_snapshot)
            new_snapshot.update(
                {
                    "name": name,
                    "description": description or None,
                    "category": category.value,
                    "implication_ids": sorted(implication_ids),
                    "aliases": sorted(a.strip() for a in aliases if a.strip()),
                }
            )

            patch = compute_patch(old_snapshot, new_snapshot)
            if not patch:
                return HTMLResponse(
                    headers={"HX-Redirect": str(request.url_for("get_tag", id=id))}
                )

            head = get_head_edit(session, "tags", id)
            session.add(
                PendingEdit(
                    entity_type="tags",
                    entity_id=id,
                    patch=patch,
                    created_by_id=current_user.id,
                    parent_id=head.id if head else None,
                )
            )

            return HTMLResponse(
                headers={
                    "HX-Redirect": str(request.url_for("get_tag", id=id))
                    + "?version=pending"
                }
            )

        tag.name = name
        tag.description = description or None
        tag.category = category

        old_implication_ids: set[int] = {t.id for t in tag.implications}
        implied_tags: Sequence[Tag] = session.scalars(
            select(Tag).where(Tag.id.in_(implication_ids))
        ).all()
        tag.implications = set(implied_tags)

        new_implication_ids: set[int] = {t.id for t in implied_tags}
        newly_added_ids: set[int] = new_implication_ids - old_implication_ids

        if newly_added_ids:
            session.flush()  # write new tag_implications rows before resolving

            newly_added_tags: list[Tag] = [
                t for t in implied_tags if t.id in newly_added_ids
            ]
            all_new_implied: set[Tag] = resolve_implications(
                initial=newly_added_tags,
                session=session,
            )

            for implied_tag in all_new_implied:
                session.execute(
                    pg_insert(pins_tags)
                    .from_select(
                        ["pin_id", "tag_id"],
                        select(
                            pins_tags.c.pin_id,
                            literal(implied_tag.id).label("tag_id"),
                        ).where(pins_tags.c.tag_id == tag.id),
                    )
                    .on_conflict_do_nothing()
                )

        tag.aliases = [TagAlias(alias=a.strip()) for a in aliases if a.strip()]

        session.flush()
        tag_id: int = tag.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_tag", id=tag_id))}
    )
