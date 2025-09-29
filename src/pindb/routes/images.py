from uuid import UUID

from fastapi.responses import FileResponse
from fastapi.routing import APIRouter

from pindb.config import CONFIGURATION

router = APIRouter(prefix="/image")


@router.get("/{guid}", response_model=None)
def get_image(guid: UUID) -> FileResponse | None:
    image_path = (CONFIGURATION.image_directory / str(guid)).resolve()

    if not image_path.exists() or not image_path.is_file():
        return None

    return FileResponse(path=image_path, media_type="image")
