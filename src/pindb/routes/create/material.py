from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import Material, session_maker
from pindb.templates.create_and_edit.material import material_form

router = APIRouter()


@router.get(path="/material")
def get_create_material(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=material_form(post_url=request.url_for("post_create_material"))
    )


@router.post(path="/material")
async def post_create_material(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        material = Material(name=name)

        session.add(instance=material)
        session.flush()
        material_id = material.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_material", id=material_id))}
    )
