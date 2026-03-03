from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.database import Material, session_maker
from pindb.templates.get.material import material_page

router = APIRouter()


@router.get(path="/material/{id}", response_model=None)
def get_material(
    request: Request,
    id: int,
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        material_obj: Material | None = session.get(entity=Material, ident=id)

        if not material_obj:
            return RedirectResponse(url="/")

        return HTMLResponse(material_page(request=request, material=material_obj))
