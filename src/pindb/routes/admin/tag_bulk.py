"""Admin-only bulk upsert for tag trees (JSON), mirroring edit/tag resolution."""

from __future__ import annotations

import json
from json import JSONDecodeError

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.database import Tag, TagCategory, session_maker
from pindb.database.joins import tag_implications
from pindb.database.tag import (
    TagAlias,
    cascade_new_implications_to_pins,
    normalize_tag_name,
)
from pindb.log import user_logger
from pindb.search.update import update_tags
from pindb.templates.admin.bulk_tags import bulk_tags_page

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

    @model_validator(mode="before")
    @classmethod
    def _coerce_shorthand(cls, data: object) -> object:
        """Accept `{...}` (single node) or `[...]` (list of nodes) as shorthand for `{"tags": [...]}`."""
        if isinstance(data, list):
            return {"tags": data}
        if isinstance(data, dict) and "tags" not in data and "name" in data:
            return {"tags": [data]}
        return data


class BulkTagUpsertResult(BaseModel):
    root_tag_ids: list[int]
    touched_tag_ids: list[int]


def _merge_tag_fields(
    *,
    tag: Tag,
    node: TagUpsertNode,
) -> None:
    """Fill empty/default scalar fields. Conflicting non-default values are kept and logged.

    Bulk import is intentionally non-destructive: existing values win. A future
    re-import that wants to overwrite must use the per-tag edit form.
    """
    if node.description and tag.description is None:
        tag.description = node.description
    elif (
        node.description
        and tag.description is not None
        and node.description.strip() != tag.description.strip()
    ):
        LOGGER.warning(
            "bulk-upsert: keeping existing description for tag id=%d name=%r "
            "(payload differs); use the tag editor to overwrite.",
            tag.id,
            tag.name,
        )

    if node.category != TagCategory.general and tag.category == TagCategory.general:
        tag.category = node.category
    elif (
        node.category != TagCategory.general
        and tag.category != TagCategory.general
        and node.category != tag.category
    ):
        LOGGER.warning(
            "bulk-upsert: keeping existing category=%s for tag id=%d name=%r "
            "(payload had category=%s); use the tag editor to overwrite.",
            tag.category.value,
            tag.id,
            tag.name,
            node.category.value,
        )


def _add_new_aliases(*, tag: Tag, node: TagUpsertNode, session: Session) -> int:
    """Insert any aliases from the payload that aren't already on the tag.

    Add-only. Returns the number of aliases inserted. Avoids the delete+reinsert
    churn (and ChangeLog noise) of ``replace_tag_aliases`` when nothing changed.
    Filters out aliases equal to the tag's own normalized name.
    """
    name_key = tag.name
    existing_normalized: set[str] = {
        normalize_tag_name(alias_row.alias) for alias_row in tag.aliases
    }
    to_add: list[str] = []
    seen: set[str] = set()
    for raw in node.aliases:
        normalized = normalize_tag_name(raw)
        if (
            not normalized
            or normalized == name_key
            or normalized in existing_normalized
            or normalized in seen
        ):
            continue
        seen.add(normalized)
        to_add.append(normalized)
    for normalized in to_add:
        tag.aliases.append(TagAlias(alias=normalized))
    if to_add:
        session.flush()
    return len(to_add)


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

        # Implications are union-only on bulk import (non-destructive merge).
        # To remove an implication, use the per-tag edit form.
        old_implication_ids: set[int] = {implied.id for implied in tag.implications}
        merged_implied: set[Tag] = set(tag.implications) | set(implied_tags)
        tag.implications = merged_implied
        new_implication_ids: set[int] = {t.id for t in merged_implied}
        newly_added_ids: set[int] = new_implication_ids - old_implication_ids

        session.flush()

        if newly_added_ids:
            cascade_new_implications_to_pins(
                tag=tag,
                newly_added_ids=newly_added_ids,
                implied_tags=merged_implied,
                session=session,
            )

        added_alias_count = _add_new_aliases(tag=tag, node=node, session=session)

        action = "created" if created else "merged"
        LOGGER.info(
            "%s tag id=%d name=%r implications=+%d (total %d) aliases=+%d (total %d)",
            action,
            tag.id,
            name_key,
            len(newly_added_ids),
            len(merged_implied),
            added_alias_count,
            len(tag.aliases),
        )
        touched.add(tag.id)
        return tag
    finally:
        visiting.discard(name_key)


def _check_no_cycles(touched_root_ids: list[int], session: Session) -> None:
    """Run the BFS implication closure from each root; raises 400 on revisit.

    Catches cycles created by mixing payload edges with pre-existing DB edges
    (the in-payload-only ``visiting`` check inside ``_upsert_tag_node`` cannot
    see those). ``resolve_implications`` itself is cycle-safe at runtime, so we
    re-implement the walk here to actively detect a back-edge.
    """
    if not touched_root_ids:
        return
    roots = session.scalars(select(Tag).where(Tag.id.in_(touched_root_ids))).all()
    for root in roots:
        seen: set[int] = {root.id}
        stack: list[int] = [root.id]
        while stack:
            current_id = stack.pop()
            child_ids = session.scalars(
                select(tag_implications.c.implied_tag_id).where(
                    tag_implications.c.tag_id == current_id
                )
            ).all()
            for child_id in child_ids:
                if child_id == root.id:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Cycle detected in tag implications: "
                            f"{root.name!r} is reachable from itself via "
                            f"existing edges."
                        ),
                    )
                if child_id in seen:
                    continue
                seen.add(child_id)
                stack.append(child_id)


def run_bulk_tag_upsert(body: BulkTagUpsertBody) -> BulkTagUpsertResult:
    """Apply upserts in one transaction; refresh Meilisearch for touched tags."""
    if not body.tags:
        raise HTTPException(
            status_code=400,
            detail="No tags supplied; payload must contain at least one tag.",
        )

    touched: set[int] = set()
    root_ids: list[int] = []
    with session_maker.begin() as session:
        for root in body.tags:
            visiting: set[str] = set()
            tag = _upsert_tag_node(
                session=session,
                node=root,
                visiting=visiting,
                touched=touched,
            )
            root_ids.append(tag.id)
        _check_no_cycles(touched_root_ids=root_ids, session=session)

    unique_sorted = sorted(touched)

    tags_to_index: list[Tag] = []
    if unique_sorted:
        with session_maker() as session:
            tags_to_index = list(
                session.scalars(
                    select(Tag)
                    .where(Tag.id.in_(unique_sorted))
                    .options(selectinload(Tag.aliases))
                ).all()
            )
    if tags_to_index:
        try:
            update_tags(tags_to_index)
        except Exception:
            LOGGER.warning(
                "bulk-upsert: Meilisearch update failed for %d tag(s); "
                "the periodic resync job will reconcile.",
                len(tags_to_index),
                exc_info=True,
            )

    return BulkTagUpsertResult(root_tag_ids=root_ids, touched_tag_ids=unique_sorted)


def _format_validation_error(exc: ValidationError) -> str:
    """Render a pydantic ValidationError as a compact, user-readable string."""
    lines: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "invalid value")
        lines.append(f"{loc or '<root>'}: {msg}")
    return "\n".join(lines)


@router.get("/tags/bulk")
def get_admin_bulk_tags(request: Request) -> HtpyResponse:
    return HtpyResponse(bulk_tags_page(request=request))


@router.post("/tags/bulk")
async def post_admin_bulk_tags(
    request: Request,
    json_text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
) -> HtpyResponse:
    text_present = bool(json_text.strip())
    file_present = file is not None and bool((file.filename or "").strip())

    if text_present and file_present:
        return HtpyResponse(
            bulk_tags_page(
                request=request,
                error_message=(
                    "Provide either pasted JSON or a file upload — not both."
                ),
            ),
            status_code=400,
        )

    raw_bytes: bytes | None = None
    if file_present and file is not None:
        raw_bytes = await file.read()
    elif text_present:
        raw_bytes = json_text.encode("utf-8")
    if raw_bytes is None or not raw_bytes.strip():
        return HtpyResponse(
            bulk_tags_page(
                request=request,
                error_message="Paste JSON in the text field or choose a JSON file.",
            ),
            status_code=400,
        )
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except JSONDecodeError as exc:
        return HtpyResponse(
            bulk_tags_page(
                request=request,
                error_message=f"Invalid JSON: {exc}",
            ),
            status_code=400,
        )
    try:
        body = BulkTagUpsertBody.model_validate(data)
    except ValidationError as exc:
        return HtpyResponse(
            bulk_tags_page(
                request=request,
                error_message=("Invalid payload:\n" + _format_validation_error(exc)),
            ),
            status_code=400,
        )
    try:
        result = run_bulk_tag_upsert(body)
    except HTTPException as exc:
        return HtpyResponse(
            bulk_tags_page(
                request=request,
                error_message=str(exc.detail),
            ),
            status_code=exc.status_code,
        )
    return HtpyResponse(
        bulk_tags_page(
            request=request,
            result=result.model_dump(mode="json"),
        )
    )


@router.post("/tags/bulk-upsert")
def post_admin_tags_bulk_upsert(body: BulkTagUpsertBody) -> JSONResponse:
    """Merge or create tags from a recursive JSON tree (name, category, aliases, implications).

    Existing tags gain new aliases and new implications; scalar fields are filled when empty
    (description) or still default (category). New implications use the same ``pins_tags``
    cascade as the tag edit form. Admin-only.
    """
    result = run_bulk_tag_upsert(body)
    return JSONResponse(content=result.model_dump(mode="json"))
