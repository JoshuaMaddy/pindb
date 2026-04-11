from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.auth import EditorUser
from pindb.database import Tag, session_maker
from pindb.routes._guards import assert_editor_can_edit
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter()


@router.get(path="/tag/{id}", response_model=None)
def get_edit_tag(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse | None:
    with session_maker() as session:
        tag: Tag | None = session.get(entity=Tag, ident=id)

        if tag is None:
            return None

        assert_editor_can_edit(tag, current_user)

        return HTMLResponse(
            content=str(
                tag_form(
                    post_url=request.url_for("post_edit_tag", id=id),
                    tag=tag,
                    request=request,
                )
            )
        )


@router.post(path="/tag/{id}", response_model=None)
def post_edit_tag(
    request: Request,
    id: int,
    current_user: EditorUser,
    name: str = Form(),
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        tag: Tag | None = session.get(entity=Tag, ident=id)

        if not tag:
            return None

        assert_editor_can_edit(tag, current_user)

        tag.name = name
        session.flush()
        tag_id: int = tag.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_tag", id=tag_id))}
    )
