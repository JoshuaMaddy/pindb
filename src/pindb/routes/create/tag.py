"""
FastAPI routes: `routes/create/tag.py`.
"""

from fastapi import Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from pindb.database import Tag, TagAlias, TagCategory, async_session_maker
from pindb.database.tag import normalize_tag_name
from pindb.htmx_toast import (
    hx_redirect_with_toast_headers,
    is_unique_violation,
    unique_constraint_response,
)
from pindb.log import user_logger
from pindb.routes._urls import slugify_for_url
from pindb.search.update import update_tag
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.create.tag")


@router.get(path="/tag")
async def get_create_tag(
    request: Request,
    duplicate_from: int | None = Query(default=None),
) -> HTMLResponse:
    duplicate_source: Tag | None = None
    if duplicate_from is not None:
        async with async_session_maker() as session:
            duplicate_source = await session.scalar(
                select(Tag)
                .where(Tag.id == duplicate_from)
                .options(selectinload(Tag.implications), selectinload(Tag.aliases))
            )
        if duplicate_source is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tag {duplicate_from} not found to duplicate.",
            )

    return HTMLResponse(
        content=str(
            tag_form(
                post_url=request.url_for("post_create_tag"),
                request=request,
                options_url=str(request.url_for("get_tag_options")),
                duplicate_source=duplicate_source,
            )
        )
    )


@router.post(path="/tag")
async def post_create_tag(
    request: Request,
    name: str = Form(),
    description: str | None = Form(default=None),
    category: TagCategory = Form(default=TagCategory.general),
    implication_ids: list[int] = Form(default_factory=list),
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    LOGGER.info(
        "Creating tag name=%r category=%s implications=%s aliases=%s",
        name,
        category.value,
        implication_ids,
        aliases,
    )
    try:
        async with async_session_maker.begin() as session:
            tag = Tag(
                name=normalize_tag_name(name),
                description=description or None,
                category=category,
            )
            session.add(instance=tag)
            await session.flush()

            if implication_ids:
                implied_tags = (
                    await session.scalars(
                        select(Tag).where(Tag.id.in_(implication_ids))
                    )
                ).all()
                tag.implications = set(implied_tags)

            tag.aliases = [
                TagAlias(alias=normalize_tag_name(a)) for a in aliases if a.strip()
            ]

            await session.flush()
            tag_id: int = tag.id
    except IntegrityError as exc:
        if not is_unique_violation(exc):
            raise
        return unique_constraint_response(request=request)

    await update_tag(tag=tag)

    LOGGER.info("Created tag id=%d name=%r", tag_id, name)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(
                request.url_for(
                    "get_tag",
                    slug=slugify_for_url(name=name, fallback="tag"),
                    id=tag_id,
                )
            ),
            message="Tag created.",
        )
    )
