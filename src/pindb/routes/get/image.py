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
    sniff_image_mime,
)

router = APIRouter()


def _original_mime_from_path(path) -> str:
    with open(path, "rb") as f:
        head = f.read(16)
    return sniff_image_mime(head)


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
        media_type = "image/webp" if thumbnail else _original_mime_from_path(path)
        return FileResponse(path=path, media_type=media_type)

    data = load_image(key)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    media_type = "image/webp" if thumbnail else sniff_image_mime(data[:16])
    return Response(content=data, media_type=media_type)
