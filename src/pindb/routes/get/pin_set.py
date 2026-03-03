from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.templates.get.pin_set import pin_set_page

router = APIRouter()


@router.get(path="/pin_set/{id}", response_model=None)
def get_pin_set(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        pin_set_obj: PinSet | None = session.get(entity=PinSet, ident=id)

        if not pin_set_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(content=pin_set_page(request=request, pin_set=pin_set_obj))
