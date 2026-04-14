from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.search.update import update_pin_set

router = APIRouter()


@router.get(path="/pin_set")
def get_create_pin_set(request: Request) -> HTMLResponse:
    from pindb.templates.create_and_edit.pin_set import pin_set_create_page

    return HTMLResponse(content=str(pin_set_create_page(request=request)))


@router.post(path="/pin_set")
def post_create_pin_set(
    request: Request,
    name: str = Form(),
    description: str | None = Form(default=None),
) -> RedirectResponse:
    with session_maker.begin() as session:
        pin_set = PinSet(
            name=name.strip(),
            description=description.strip() if description else None,
        )
        session.add(pin_set)
        session.flush()
        set_id: int = pin_set.id

    update_pin_set(pin_set=pin_set)

    return RedirectResponse(
        url=str(request.url_for("get_edit_set", set_id=set_id)),
        status_code=303,
    )
