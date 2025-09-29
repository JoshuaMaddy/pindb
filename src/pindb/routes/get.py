from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import session_maker
from pindb.database.pin import Pin
from pindb.database.shop import Shop
from pindb.templates.get.pin import pin_page
from pindb.templates.get.shop import shop_page

router = APIRouter(prefix="/get")


@router.get("/pin/{id}")
def get_pin(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_obj = session.get(Pin, id)

        if not pin_obj:
            return None

        return HTMLResponse(pin_page(request=request, pin=pin_obj))


@router.get("/shop/{id}")
def get_shop(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        shop_obj = session.get(Shop, id)

        if not shop_obj:
            return None

        return HTMLResponse(shop_page(request=request, shop=shop_obj))
