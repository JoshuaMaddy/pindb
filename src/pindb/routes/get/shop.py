from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import Shop, session_maker
from pindb.templates.get.shop import shop_page

router = APIRouter()


@router.get(path="/shop/{id}", response_model=None)
def get_shop(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        shop_obj: Shop | None = session.get(entity=Shop, ident=id)

        if not shop_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(content=shop_page(request=request, shop=shop_obj))
