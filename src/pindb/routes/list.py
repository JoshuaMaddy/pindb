from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.templates.create.pin import pin_form
from pindb.templates.create.material import material_form


router = APIRouter(prefix="/list")


@router.get("/material")
def get_materials(request: Request) -> :
    return HTMLResponse(material_form)
