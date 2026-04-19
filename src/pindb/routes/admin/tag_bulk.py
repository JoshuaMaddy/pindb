"""Admin-only bulk upsert for tag trees (JSON), mirroring edit/tag resolution."""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from pindb.database import Tag, TagCategory, session_maker
from pindb.database.joins import pins_tags
from pindb.database.tag import (
    normalize_tag_name,
    replace_tag_aliases,
    resolve_implications,
)
from pindb.log import user_logger
from pindb.search.update import update_tags

LOGGER = user_logger("pindb.routes.admin.tag_bulk")

router = APIRouter()


class TagUpsertNode(BaseModel):
    """Recursive tag payload (e.g. Serebii JSON export)."""

    name: str
    category: TagCategory = TagCategory.general
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    implications: list[TagUpsertNode] = Field(default_factory=list)


class BulkTagUpsertBody(BaseModel):
    tags: list[TagUpsertNode]


class BulkTagUpsertResult(BaseModel):
    root_tag_ids: list[int]
    touched_tag_ids: list[int]


def _cascade_new_implications_to_pins(
    *,
    tag: Tag,
    newly_added_ids: set[int],
    implied_tags: list[Tag],
    session: Session,
) -> None:
    """Mirror ``post_edit_tag`` / pending approval: new implications propagate to pins."""
    if not newly_added_ids:
        return
    newly_added_tags: list[Tag] = [
        implied_tag for implied_tag in implied_tags if implied_tag.id in newly_added_ids
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


def _merge_tag_fields(
    *,
    tag: Tag,
    node: TagUpsertNode,
) -> None:
    if tag.description is None and node.description:
        tag.description = node.description
    if tag.category == TagCategory.general and node.category != TagCategory.general:
        tag.category = node.category


def _merged_alias_strings(*, tag: Tag, node: TagUpsertNode, name_key: str) -> list[str]:
    existing: list[str] = [alias_row.alias for alias_row in tag.aliases]
    combined: list[str] = list(existing) + list(node.aliases)
    result: list[str] = []
    seen: set[str] = set()
    for raw in combined:
        normalized = normalize_tag_name(raw)
        if not normalized or normalized == name_key or normalized in seen:
            continue
        seen.add(normalized)
        result.append(raw.strip())
    return result


def _upsert_tag_node(
    *,
    session: Session,
    node: TagUpsertNode,
    visiting: set[str],
    touched: set[int],
) -> Tag:
    name_key = normalize_tag_name(node.name)
    if not name_key:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty.")
    if name_key in visiting:
        raise HTTPException(
            status_code=400,
            detail=f"Cycle in tag implications involving {name_key!r}.",
        )
    visiting.add(name_key)
    try:
        implied_tags: list[Tag] = []
        seen_child: set[str] = set()
        for child in node.implications:
            child_key = normalize_tag_name(child.name)
            if not child_key or child_key in seen_child:
                continue
            seen_child.add(child_key)
            implied_tags.append(
                _upsert_tag_node(
                    session=session,
                    node=child,
                    visiting=visiting,
                    touched=touched,
                )
            )

        tag: Tag | None = session.scalar(
            select(Tag)
            .where(Tag.name == name_key)
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
        )
        created = tag is None
        if tag is None:
            tag = Tag(
                name=name_key,
                description=node.description,
                category=node.category,
            )
            session.add(tag)
            session.flush()
        else:
            _merge_tag_fields(tag=tag, node=node)

        old_implication_ids: set[int] = {implied.id for implied in tag.implications}
        merged_implied: set[Tag] = set(tag.implications) | set(implied_tags)
        tag.implications = merged_implied
        new_implication_ids: set[int] = {t.id for t in merged_implied}
        newly_added_ids: set[int] = new_implication_ids - old_implication_ids

        session.flush()

        if newly_added_ids:
            _cascade_new_implications_to_pins(
                tag=tag,
                newly_added_ids=newly_added_ids,
                implied_tags=list(merged_implied),
                session=session,
            )

        merged_aliases = _merged_alias_strings(tag=tag, node=node, name_key=name_key)
        replace_tag_aliases(tag=tag, aliases=merged_aliases, session=session)

        session.flush()

        action = "created" if created else "merged"
        LOGGER.info(
            "%s tag id=%d name=%r implications=%d aliases=%d",
            action,
            tag.id,
            name_key,
            len(merged_implied),
            len(merged_aliases),
        )
        touched.add(tag.id)
        return tag
    finally:
        visiting.discard(name_key)


def run_bulk_tag_upsert(body: BulkTagUpsertBody) -> BulkTagUpsertResult:
    """Apply upserts in one transaction; refresh Meilisearch for touched tags."""
    touched: set[int] = set()
    root_ids: list[int] = []
    with session_maker.begin() as session:
        visiting: set[str] = set()
        for root in body.tags:
            tag = _upsert_tag_node(
                session=session,
                node=root,
                visiting=visiting,
                touched=touched,
            )
            root_ids.append(tag.id)
        unique_sorted = sorted(touched)

    tags_to_index: list[Tag] = []
    with session_maker() as session:
        for tag_id in unique_sorted:
            indexed = session.scalar(
                select(Tag).where(Tag.id == tag_id).options(selectinload(Tag.aliases))
            )
            if indexed is not None:
                tags_to_index.append(indexed)
    if tags_to_index:
        update_tags(tags_to_index)

    return BulkTagUpsertResult(root_tag_ids=root_ids, touched_tag_ids=unique_sorted)


@router.post("/tags/bulk-upsert")
def post_admin_tags_bulk_upsert(body: BulkTagUpsertBody) -> JSONResponse:
    """Merge or create tags from a recursive JSON tree (name, category, aliases, implications).

    Existing tags gain new aliases and new implications; scalar fields are filled when empty
    (description) or still default (category). New implications use the same ``pins_tags``
    cascade as the tag edit form. Admin-only.
    """
    result = run_bulk_tag_upsert(body)
    return JSONResponse(content=result.model_dump())
