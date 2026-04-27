"""
FastAPI routes: `routes/create/pin_set.py`.
"""

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.htmx_toast import redirect_or_htmx_toast
from pindb.log import user_logger
from pindb.search.update import update_pin_set

router = APIRouter()

LOGGER = user_logger("pindb.routes.create.pin_set")


@router.get(path="/pin_set")
def get_create_pin_set(request: Request) -> HtpyResponse:
    from pindb.templates.create_and_edit.pin_set import pin_set_create_page

    return HtpyResponse(pin_set_create_page(request=request))


@router.post(path="/pin_set", response_model=None)
def post_create_pin_set(
    request: Request,
    name: str = Form(),
    description: str | None = Form(default=None),
) -> HTMLResponse | RedirectResponse:
    LOGGER.info("Creating pin_set name=%r", name)
    with session_maker.begin() as session:
        pin_set = PinSet(
            name=name.strip(),
            description=description.strip() if description else None,
        )
        session.add(pin_set)
        session.flush()
        set_id: int = pin_set.id

    update_pin_set(pin_set=pin_set)
    LOGGER.info("Created pin_set id=%d name=%r", set_id, name)

    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(request.url_for("get_edit_set", set_id=set_id)),
        message="Pin set created.",
    )
