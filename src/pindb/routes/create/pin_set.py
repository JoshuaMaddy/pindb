from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.templates.create_and_edit.pin_set import pin_set_form

router = APIRouter()


@router.get(path="/pin_set")
def get_create_pin_set(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=pin_set_form(post_url=request.url_for("post_create_pin_set"))
    )


@router.post(path="/pin_set")
def post_create_pin_set(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_set = PinSet(name=name)

        session.add(instance=pin_set)
        session.flush()
        pin_set_id = pin_set.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_pin_set", id=pin_set_id))}
    )
