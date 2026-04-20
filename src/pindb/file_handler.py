import io
import uuid
from math import floor
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import UploadFile

from pindb.config import CONFIGURATION

MAX_IMAGE_BYTES = 20 * 1024 * 1024
THUMBNAIL_SUFFIX = ".thumbnail"
_THUMBNAIL_DIM = 256

# Clamp PIL's decompression-bomb guard below the default (~89 MP). A
# 20 MB JPEG/PNG can still decode into gigabytes of RAM at the default
# ceiling; 24 MP covers every sane real-world photo and rejects the rest
# as a DecompressionBombError before allocation.
Image.MAX_IMAGE_PIXELS = 24_000_000


def _make_thumbnail_bytes(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data))
    aspect = image.width / image.height
    if aspect >= 1:
        w, h = _THUMBNAIL_DIM, floor(_THUMBNAIL_DIM / aspect)
    else:
        w, h = floor(_THUMBNAIL_DIM * aspect), _THUMBNAIL_DIM
    buf = io.BytesIO()
    image.resize((int(w), int(h))).save(buf, format="webp")
    return buf.getvalue()


def _strip_metadata(data: bytes) -> bytes:
    """Re-encode image without EXIF / ICC / XMP metadata.

    Prevents leaking GPS coordinates, device info, and other embedded
    metadata from user uploads. Preserves format (JPEG/PNG/WebP/etc) and
    pixel data; drops everything else.
    """
    img = Image.open(io.BytesIO(data))
    fmt = img.format or "JPEG"
    clean = Image.new(img.mode, img.size)
    clean.paste(img)
    buf = io.BytesIO()
    clean.save(buf, format=fmt)
    return buf.getvalue()


class FilesystemBackend:
    def __init__(self, directory: Path) -> None:
        self._dir = directory

    def save(self, key: str, data: bytes) -> None:
        (self._dir / key).write_bytes(data)

    def load(self, key: str) -> bytes | None:
        path = self._dir / key
        return path.read_bytes() if path.is_file() else None

    def file_path(self, key: str) -> Path | None:
        p = self._dir / key
        return p if p.is_file() else None

    def list_keys(self) -> list[str]:
        return [
            f.name
            for f in self._dir.iterdir()
            if f.is_file() and not f.name.endswith(THUMBNAIL_SUFFIX)
        ]


class R2Backend:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{CONFIGURATION.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=CONFIGURATION.r2_access_key_id,
            aws_secret_access_key=CONFIGURATION.r2_secret_access_key,
            region_name="auto",
        )
        self._bucket = CONFIGURATION.r2_bucket

    def save(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def load(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError:
            return None

    def public_url(self, key: str) -> str | None:
        if CONFIGURATION.r2_public_url:
            return f"{CONFIGURATION.r2_public_url.rstrip('/')}/{key}"
        return None

    def list_keys(self) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket):
            for obj in page.get("Contents", []):
                k: str = obj["Key"]
                if not k.endswith(THUMBNAIL_SUFFIX):
                    keys.append(k)
        return keys


_backend: FilesystemBackend | R2Backend | None = None


def get_backend() -> FilesystemBackend | R2Backend:
    global _backend
    if _backend is None:
        if CONFIGURATION.image_backend == "r2":
            _backend = R2Backend()
        else:
            assert CONFIGURATION.image_directory is not None
            _backend = FilesystemBackend(CONFIGURATION.image_directory)
    return _backend


def image_file_path(key: str) -> Path | None:
    backend = get_backend()
    if isinstance(backend, FilesystemBackend):
        return backend.file_path(key)
    return None


def image_public_url(key: str) -> str | None:
    backend = get_backend()
    if isinstance(backend, R2Backend):
        return backend.public_url(key)
    return None


def load_image(key: str) -> bytes | None:
    return get_backend().load(key)


def sniff_image_mime(data: bytes) -> str:
    """Return an ``image/*`` MIME type by magic-byte sniffing.

    Originals are stored without an extension and without metadata, so
    we cannot rely on the filesystem or the upload's Content-Type.
    Returns ``application/octet-stream`` for unrecognised bytes so the
    browser does not try to render an unexpected format as an image.
    """
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"\x00\x00\x00\x0c" and data[4:8] == b"jP  ":
        return "image/jp2"
    if data.startswith(b"BM"):
        return "image/bmp"
    return "application/octet-stream"


def ensure_thumbnail(guid_str: str) -> bool:
    """Backfill thumbnail for legacy filesystem images that predate eager generation."""
    key = f"{guid_str}{THUMBNAIL_SUFFIX}"
    backend = get_backend()
    if not isinstance(backend, FilesystemBackend):
        return backend.load(key) is not None
    if backend.file_path(key) is not None:
        return True
    orig = backend.file_path(guid_str)
    if orig is None:
        return False
    backend.save(key, _make_thumbnail_bytes(orig.read_bytes()))
    return True


async def save_image(file: UploadFile | Path) -> uuid.UUID:
    data = await file.read() if isinstance(file, UploadFile) else file.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 20 MB limit")
    try:
        stripped = _strip_metadata(data)
        thumbnail = _make_thumbnail_bytes(stripped)
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=413, detail="Image dimensions too large."
        ) from exc
    file_uuid = uuid.uuid4()
    key = str(file_uuid)
    backend = get_backend()
    backend.save(key, stripped)
    backend.save(f"{key}{THUMBNAIL_SUFFIX}", thumbnail)
    return file_uuid
