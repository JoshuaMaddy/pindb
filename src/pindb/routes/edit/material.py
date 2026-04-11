from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.auth import EditorUser
from pindb.database import Material, session_maker
from pindb.routes._guards import assert_editor_can_edit
from pindb.templates.create_and_edit.material import material_form

router = APIRouter()


@router.get(path="/material/{id}", response_model=None)
def get_edit_material(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse | None:
    with session_maker() as session:
        material: Material | None = session.get(entity=Material, ident=id)

        if material is None:
            return None

        assert_editor_can_edit(material, current_user)

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
    current_user: EditorUser,
    name: str = Form(),
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        material: Material | None = session.get(entity=Material, ident=id)

        if not material:
            return None

        assert_editor_can_edit(material, current_user)

        material.name = name
        session.flush()
        material_id: int = material.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_material", id=material_id))}
    )
