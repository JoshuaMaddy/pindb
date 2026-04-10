from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import Tag, session_maker
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()


@router.get(path="/tag")
def get_create_tag(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=tag_form(
            post_url=request.url_for("post_create_tag"),
            request=request,
        )
    )


@router.post(path="/tag")
def post_create_tag(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        tag = Tag(name=name)

        session.add(instance=tag)
        session.flush()
        tag_id: int = tag.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_tag", id=tag_id))}
    )
