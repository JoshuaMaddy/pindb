"""
FastAPI routes: `routes/get/image.py`.
"""

from uuid import UUID

from fastapi import HTTPException, Query, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.routing import APIRouter

from pindb.file_handler import (
    DEFAULT_THUMB_DISPLAY_W,
    THUMBNAIL_SIZES,
    THUMBNAIL_SUFFIX,
    ensure_legacy_thumbnail_on_disk,
    ensure_sized_thumbnail_on_disk,
    image_file_path,
    image_public_url,
    load_image,
    sniff_image_mime,
    thumbnail_storage_key,
)
from pindb.http_caching import IMAGE_CACHE_CONTROL

router = APIRouter()


def _original_mime_from_path(path) -> str:
    with open(path, "rb") as f:
        head = f.read(16)
    return sniff_image_mime(head)


def _key_is_present(key: str) -> bool:
    if image_file_path(key) is not None:
        return True
    return load_image(key) is not None


@router.get(path="/image/{guid}", response_model=None, name="get_image")
async def get_image(
    guid: UUID,
    thumbnail: bool = False,
    w: int | None = Query(None),
) -> FileResponse | RedirectResponse | Response:
    guid_str = str(guid)

    if w is not None:
        if w not in THUMBNAIL_SIZES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid w; allowed values: {', '.join(str(x) for x in THUMBNAIL_SIZES)}",
            )
        ensure_sized_thumbnail_on_disk(guid_str, w)
        key = thumbnail_storage_key(guid_str, w)
        is_webp = True
        if not _key_is_present(key):
            raise HTTPException(status_code=404, detail="Image not found")
    elif thumbnail:
        ensure_sized_thumbnail_on_disk(guid_str, DEFAULT_THUMB_DISPLAY_W)
        key200 = thumbnail_storage_key(guid_str, DEFAULT_THUMB_DISPLAY_W)
        if _key_is_present(key200):
            key = key200
        else:
            ensure_legacy_thumbnail_on_disk(guid_str)
            key = f"{guid_str}{THUMBNAIL_SUFFIX}"
            if not _key_is_present(key):
                raise HTTPException(status_code=404, detail="Image not found")
        is_webp = True
    else:
        key = guid_str
        is_webp = False

    pub_url = image_public_url(key)
    if pub_url:
        return RedirectResponse(
            url=pub_url,
            status_code=302,
            headers={"Cache-Control": IMAGE_CACHE_CONTROL},
        )

    path = image_file_path(key)
    if path is not None:
        media_type = "image/webp" if is_webp else _original_mime_from_path(path)
        return FileResponse(
            path=path,
            media_type=media_type,
            headers={"Cache-Control": IMAGE_CACHE_CONTROL},
        )

    data = load_image(key)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    media_type = "image/webp" if is_webp else sniff_image_mime(data[:16])
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": IMAGE_CACHE_CONTROL},
    )
