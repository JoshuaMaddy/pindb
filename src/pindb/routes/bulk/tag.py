"""FastAPI routes: `routes/bulk/tag.py`.

JSON bulk creation of tags with cross-row implications. Per-row error
isolation: each row attempts its own savepoint; failures don't sink the
others. Editor submissions land pending sharing one ``bulk_id``; admin
creations auto-approve via the shared ``before_flush`` audit hook.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Tag, TagCategory, async_session_maker
from pindb.database.tag import normalize_tag_name, replace_tag_aliases
from pindb.log import user_logger
from pindb.routes.bulk._tag_helpers import (
    CycleError,
    find_duplicate_indices,
    topo_sort_indices,
)
from pindb.search.update import update_tag
from pindb.templates.bulk.tag import bulk_tag_page

LOGGER = user_logger("pindb.routes.bulk.tag")

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BulkTagRow(BaseModel):
    client_id: str
    name: str
    category: TagCategory = TagCategory.general
    description: str | None = None
    aliases: list[str] = []
    implication_names: list[str] = []


class BulkTagInput(BaseModel):
    tags: list[BulkTagRow]


class BulkTagRowResult(BaseModel):
    client_id: str
    index: int
    success: bool
    tag_id: int | None = None
    tag_name: str | None = None
    error: str | None = None


class BulkTagResult(BaseModel):
    results: list[BulkTagRowResult]
    created_count: int
    failed_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(path="/tag")
async def get_bulk_tag(request: Request) -> HtpyResponse:
    options_base_url: str = str(
        request.url_for("get_bulk_options", entity_type="placeholder")
    ).removesuffix("/placeholder")

    return HtpyResponse(
        bulk_tag_page(
            submit_url=str(request.url_for("post_bulk_tags")),
            options_base_url=options_base_url,
            request=request,
        )
    )


@router.post(path="/tag")
async def post_bulk_tags(
    body: BulkTagInput,
    current_user: EditorUser,
) -> JSONResponse:
    bulk_id: UUID = uuid4()
    LOGGER.info("Bulk-creating %d tags bulk_id=%s", len(body.tags), bulk_id)

    # ---------- Pre-process: normalize names + implications ---------------
    normalized_names: list[str] = [normalize_tag_name(row.name) for row in body.tags]
    normalized_impls: list[list[str]] = [
        # dedupe + drop empties
        list(
            dict.fromkeys(
                normalize_tag_name(n) for n in row.implication_names if n.strip()
            )
        )
        for row in body.tags
    ]

    results: list[BulkTagRowResult] = [
        BulkTagRowResult(
            client_id=row.client_id,
            index=index,
            success=False,
            tag_name=normalized_names[index],
        )
        for index, row in enumerate(body.tags)
    ]
    failed: set[int] = set()

    # In-batch duplicate names: every offending row fails.
    duplicates: dict[str, list[int]] = find_duplicate_indices(normalized_names)
    for name, indices in duplicates.items():
        for idx in indices:
            failed.add(idx)
            results[idx].error = f"Duplicate name within batch: {name!r}"

    # Cycle detection (across all rows, regardless of duplicate failures so we
    # surface the cycle clearly when both apply).
    try:
        order = topo_sort_indices(normalized_names, normalized_impls)
    except CycleError as cycle:
        for idx, name in enumerate(normalized_names):
            if name in cycle.names:
                failed.add(idx)
                if results[idx].error is None:
                    results[
                        idx
                    ].error = f"Cycle in implications among: {sorted(cycle.names)}"
        order = list(range(len(body.tags)))

    # ---------- Persist rows in dependency order ---------------------------
    # We pre-check name collisions against the DB instead of catching
    # IntegrityError + savepoint-rolling-back. Reason: a failed flush leaves
    # entries queued in the `audit_events._pending_audit` ContextVar (which
    # only gets drained by `after_flush`, which doesn't run when flush errors
    # mid-statement). Those stale entries then poison the next row's flush
    # via NULL `change_log.entity_id`. Pre-checking sidesteps the whole mess.
    created_tag_ids: list[int] = []
    async with async_session_maker.begin() as outer_session:
        name_to_index: dict[str, int] = {
            name: idx for idx, name in enumerate(normalized_names) if name
        }
        # In-batch: row index -> created Tag id (only for rows that succeed).
        in_batch_created: dict[int, int] = {}

        for index in order:
            if index in failed:
                continue

            row = body.tags[index]
            row_name = normalized_names[index]

            if not row_name:
                failed.add(index)
                results[index].error = "Name is required"
                continue

            # Pre-check: collision with any non-deleted tag (approved, pending,
            # or rejected). The partial unique index on tags.name only covers
            # `WHERE deleted_at IS NULL`, so a soft-deleted tag with the same
            # name is fine to reuse — that's why we don't pass include_deleted.
            existing_collision = await outer_session.scalar(
                select(Tag.id)
                .where(Tag.name == row_name)
                .execution_options(include_pending=True)
            )
            if existing_collision is not None:
                failed.add(index)
                results[index].error = f"Tag with name {row_name!r} already exists"
                continue

            try:
                # Resolve implications: in-batch siblings first (already
                # created earlier in this loop thanks to topo order); fall back
                # to DB lookup; otherwise create-on-the-fly so a cross-row
                # reference to a brand-new DB tag still works.
                implication_tags: set[Tag] = set()
                for impl_name in normalized_impls[index]:
                    sibling_id = in_batch_created.get(name_to_index.get(impl_name, -1))
                    if sibling_id is not None:
                        implication_tags.add(
                            await outer_session.get_one(Tag, sibling_id)
                        )
                        continue
                    existing_impl = await outer_session.scalar(
                        select(Tag)
                        .where(Tag.name == impl_name)
                        .execution_options(include_pending=True)
                    )
                    if existing_impl is None:
                        existing_impl = Tag(name=impl_name)
                        outer_session.add(existing_impl)
                        await outer_session.flush()
                        existing_impl.bulk_id = bulk_id
                        await outer_session.flush()
                    implication_tags.add(existing_impl)

                tag = Tag(
                    name=row_name,
                    description=row.description or None,
                    category=row.category,
                )
                outer_session.add(tag)
                await outer_session.flush()
                tag.bulk_id = bulk_id
                tag.implications = implication_tags
                await replace_tag_aliases(tag, row.aliases, outer_session)
                await outer_session.flush()

                in_batch_created[index] = tag.id
                created_tag_ids.append(tag.id)
                results[index].success = True
                results[index].tag_id = tag.id
                results[index].tag_name = tag.name
            except IntegrityError as error:
                # Should be rare given the pre-check; aliases or another
                # constraint may still race. Re-raise to abort the batch
                # rather than silently corrupt the audit queue.
                LOGGER.error(
                    "row[%d] %r integrity failure: %s",
                    index,
                    row_name,
                    error.orig,
                )
                raise

    # ---------- Post-write Meili sync (DB session is now closed) ----------
    if created_tag_ids:
        async with async_session_maker() as read_session:
            persisted = (
                await read_session.scalars(
                    select(Tag)
                    .where(Tag.id.in_(created_tag_ids))
                    .options(selectinload(Tag.aliases))
                )
            ).all()
            for tag in persisted:
                await update_tag(tag=tag)

    created = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)
    LOGGER.info(
        "Bulk tag submission complete bulk_id=%s created=%d failed=%d",
        bulk_id,
        created,
        failed_count,
    )

    return JSONResponse(
        content=BulkTagResult(
            results=results,
            created_count=created,
            failed_count=failed_count,
        ).model_dump()
    )
