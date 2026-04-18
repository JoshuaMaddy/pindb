from uuid import UUID

from fastapi import HTTPException, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.file_handler import (
    THUMBNAIL_SUFFIX,
    ensure_thumbnail,
    image_file_path,
    image_public_url,
    load_image,
)

router = APIRouter()


@router.get(path="/image/{guid}", response_model=None)
async def get_image(
    guid: UUID,
    thumbnail: bool = False,
) -> FileResponse | RedirectResponse | Response:
    key = f"{guid}{THUMBNAIL_SUFFIX}" if thumbnail else str(guid)

    pub_url = image_public_url(key)
    if pub_url:
        return RedirectResponse(url=pub_url, status_code=302)

    path = image_file_path(key)
    if path is None and thumbnail:
        if not ensure_thumbnail(str(guid)):
            raise HTTPException(status_code=404, detail="Image not found")
        path = image_file_path(key)
    if path is not None:
        return FileResponse(
            path=path, media_type="image/webp" if thumbnail else "image"
        )

    data = load_image(key)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type="image/webp" if thumbnail else "image")
