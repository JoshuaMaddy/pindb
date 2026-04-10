from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import Material, session_maker
from pindb.templates.create_and_edit.material import material_form

router = APIRouter()


@router.get(path="/material/{id}", response_model=None)
def get_edit_material(
    request: Request,
    id: int,
) -> HTMLResponse | None:
    with session_maker() as session:
        material: Material | None = session.get(entity=Material, ident=id)

        if material is None:
            return None

        return HTMLResponse(
            content=str(
                material_form(
                    post_url=request.url_for("post_edit_material", id=id),
                    material=material,
                    request=request,
                )
            )
        )


@router.post(path="/material/{id}", response_model=None)
def post_edit_material(
    request: Request,
    id: int,
    name: str = Form(),
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        material: Material | None = session.get(entity=Material, ident=id)

        if not material:
            return None

        material.name = name
        session.flush()
        material_id: int = material.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_material", id=material_id))}
    )
