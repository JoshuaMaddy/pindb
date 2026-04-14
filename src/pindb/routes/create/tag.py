from typing import Sequence

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import Tag, TagAlias, TagCategory, session_maker
from pindb.search.update import update_tag
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()


@router.get(path="/tag")
def get_create_tag(request: Request) -> HTMLResponse:
    with session_maker() as session:
        all_tags: Sequence[Tag] = session.scalars(
            select(Tag).order_by(Tag.name.asc())
        ).all()
        return HTMLResponse(
            content=str(
                tag_form(
                    post_url=request.url_for("post_create_tag"),
                    request=request,
                    all_tags=list(all_tags),
                )
            )
        )


@router.post(path="/tag")
def post_create_tag(
    request: Request,
    name: str = Form(),
    description: str | None = Form(default=None),
    category: TagCategory = Form(default=TagCategory.general),
    implication_ids: list[int] = Form(default_factory=list),
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    with session_maker.begin() as session:
        tag = Tag(name=name, description=description or None, category=category)
        session.add(instance=tag)
        session.flush()

        if implication_ids:
            implied_tags = session.scalars(
                select(Tag).where(Tag.id.in_(implication_ids))
            ).all()
            tag.implications = set(implied_tags)

        tag.aliases = [TagAlias(alias=a.strip()) for a in aliases if a.strip()]

        session.flush()
        tag_id: int = tag.id

    update_tag(tag=tag)

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_tag", id=tag_id))}
    )
