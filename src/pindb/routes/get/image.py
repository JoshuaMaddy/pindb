from pathlib import Path
from uuid import UUID

from fastapi.responses import FileResponse
from fastapi.routing import APIRouter

from pindb.config import CONFIGURATION
from pindb.file_handler import create_thumbnail

router = APIRouter()


@router.get(path="/image/{guid}", response_model=None)
async def get_image(
    guid: UUID,
    thumbnail: bool = False,
) -> FileResponse | None:
    image_path: Path = (CONFIGURATION.image_directory / str(guid)).resolve()

    if not image_path.exists() or not image_path.is_file():
        return None

    if thumbnail:
        image_path: Path = (
            CONFIGURATION.image_directory / f"{guid}.thumbnail"
        ).resolve()

        if not image_path.exists():
            await create_thumbnail(file_uuid=str(guid))

    return FileResponse(path=image_path, media_type="image")
