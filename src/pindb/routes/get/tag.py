from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import Tag, session_maker
from pindb.templates.get.tag import tag_page

router = APIRouter()


@router.get(path="/tag/{id}", response_model=None)
def get_tag(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        tag_obj: Tag | None = session.get(entity=Tag, ident=id)

        if not tag_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(content=tag_page(request=request, tag=tag_obj))
