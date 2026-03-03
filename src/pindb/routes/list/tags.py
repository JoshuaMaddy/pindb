from typing import Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.tag import Tag
from pindb.templates.list.tags import tags_list

router = APIRouter()


@router.get(path="/tags")
def get_list_tags(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        tags: Sequence[Tag] = session.scalars(
            statement=select(Tag).order_by(Tag.name.asc())
        ).all()

        return HTMLResponse(content=tags_list(request=request, tags=tags))
