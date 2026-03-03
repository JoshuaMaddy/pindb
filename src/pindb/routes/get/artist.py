from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import Artist, session_maker
from pindb.templates.get.artist import artist_page

router = APIRouter()


@router.get(path="/artist/{id}", response_model=None)
def get_artist(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        artist_obj: Artist | None = session.get(entity=Artist, ident=id)

        if not artist_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(content=artist_page(request=request, artist=artist_obj))
