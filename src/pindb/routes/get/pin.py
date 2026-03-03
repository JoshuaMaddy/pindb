from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import Pin, session_maker
from pindb.templates.get.pin import pin_page

router = APIRouter()


@router.get(path="/pin/{id}", response_model=None)
def get_pin(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        pin_obj: Pin | None = session.get(entity=Pin, ident=id)

        if not pin_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(content=pin_page(request=request, pin=pin_obj))
