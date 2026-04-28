"""Pin image storage, ingest, and serving helpers.

Images are stored as opaque UUID keys (no extension). Uploads are capped at
``MAX_IMAGE_BYTES``, stripped of embedded metadata, and written with WebP
sidecars ``{uuid}.thumb.{w}`` for each width in ``THUMBNAIL_SIZES``. The active
backend comes from ``CONFIGURATION`` (local directory or Cloudflare R2).

Legacy data may still have a single ``{uuid}.thumbnail`` (256px WebP).
"""

import io
import re
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
# Fixed long-edge pixel sizes for stored WebP thumbnails.
THUMBNAIL_SIZES: tuple[int, ...] = (50, 100, 200, 400, 600)
# Default for legacy ``?thumbnail=true`` (maps to ``.thumb.200`` when present).
DEFAULT_THUMB_DISPLAY_W = 200
# Long edge for historic ``{uuid}.thumbnail`` sidecars only.
_LEGACY_THUMB_DIM = 256

_ORIGINAL_KEY_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z",
    re.I,
)

# Clamp PIL's decompression-bomb guard below the default (~89 MP). A
# 20 MB JPEG/PNG can still decode into gigabytes of RAM at the default
# ceiling; 24 MP covers every sane real-world photo and rejects the rest
# as a DecompressionBombError before allocation.
Image.MAX_IMAGE_PIXELS = 24_000_000


def is_original_image_key(name: str) -> bool:
    """Return True if *name* is a bare UUID key (original image), not a sidecar."""
    return bool(_ORIGINAL_KEY_PATTERN.fullmatch(name))


def thumbnail_storage_key(guid_str: str, w: int) -> str:
    """Object key for a sized WebP thumbnail: ``{uuid}.thumb.{w}``."""
    if w not in THUMBNAIL_SIZES:
        raise ValueError(
            f"Invalid thumbnail width {w}; expected one of {THUMBNAIL_SIZES}"
        )
    return f"{guid_str}.thumb.{w}"


def _thumbnail_webp_from_image(image: Image.Image, max_dim: int) -> bytes:
    aspect = image.width / image.height
    if aspect >= 1:
        width, height = max_dim, floor(max_dim / aspect)
    else:
        width, height = floor(max_dim * aspect), max_dim
    buffer = io.BytesIO()
    image.resize((int(width), int(height))).save(buffer, format="webp")
    return buffer.getvalue()


def _make_thumbnail_bytes(data: bytes, max_dim: int) -> bytes:
    """Build a WebP thumbnail from raw image bytes at *max_dim* on the long edge."""
    image = Image.open(io.BytesIO(data))
    return _thumbnail_webp_from_image(image, max_dim)


def _strip_metadata(data: bytes) -> bytes:
    """Re-encode an image without EXIF, ICC, or XMP metadata.

    Prevents leaking GPS coordinates, device info, and other embedded
    metadata from user uploads. Preserves format (JPEG/PNG/WebP/etc.) and
    pixel data; drops everything else.

    Args:
        data (bytes): Encoded image bytes.

    Returns:
        bytes: Re-encoded image bytes with metadata removed.
    """
    source_image = Image.open(io.BytesIO(data))
    image_format = source_image.format or "JPEG"
    clean_image = Image.new(source_image.mode, source_image.size)
    clean_image.paste(source_image)
    buffer = io.BytesIO()
    clean_image.save(buffer, format=image_format)
    return buffer.getvalue()


class FilesystemBackend:
    """Read and write image blobs as files under a single directory."""

    def __init__(self, directory: Path) -> None:
        """Create a backend rooted at *directory*.

        Args:
            directory (Path): Directory in which UUID keys are stored as
                filenames.
        """
        self._dir = directory

    def save(self, key: str, data: bytes) -> None:
        """Persist *data* under *key* in the backend directory.

        Args:
            key (str): Filename fragment (typically a UUID string).
            data (bytes): Raw bytes to write.
        """
        (self._dir / key).write_bytes(data)

    def load(self, key: str) -> bytes | None:
        """Load *key* from disk if the file exists.

        Args:
            key (str): Filename fragment under the backend directory.

        Returns:
            bytes | None: File contents, or ``None`` if missing.
        """
        path = self._dir / key
        return path.read_bytes() if path.is_file() else None

    def file_path(self, key: str) -> Path | None:
        """Resolve *key* to a concrete path when the file exists.

        Args:
            key (str): Filename fragment under the backend directory.

        Returns:
            Path | None: Path to the file, or ``None`` if it does not exist.
        """
        path = self._dir / key
        return path if path.is_file() else None

    def list_keys(self) -> list[str]:
        """List stored original image keys (bare UUID filenames only).

        Returns:
            list[str]: Basenames that match the original UUID pattern.
        """
        return [
            child_path.name
            for child_path in self._dir.iterdir()
            if child_path.is_file() and is_original_image_key(child_path.name)
        ]


class R2Backend:
    """S3-compatible access to a Cloudflare R2 bucket from app configuration."""

    def __init__(self) -> None:
        """Build a boto3 S3 client and bucket handle from ``CONFIGURATION``."""
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{CONFIGURATION.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=CONFIGURATION.r2_access_key_id,
            aws_secret_access_key=CONFIGURATION.r2_secret_access_key,
            region_name="auto",
        )
        self._bucket = CONFIGURATION.r2_bucket

    def save(self, key: str, data: bytes) -> None:
        """Upload *data* to R2 at *key*.

        Args:
            key (str): Object key in the bucket.
            data (bytes): Object body.
        """
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def load(self, key: str) -> bytes | None:
        """Download *key* from R2, swallowing missing-object errors.

        Args:
            key (str): Object key in the bucket.

        Returns:
            bytes | None: Object bytes, or ``None`` if the object is absent
                or the request fails with ``ClientError``.
        """
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except ClientError:
            return None

    def public_url(self, key: str) -> str | None:
        """Return a public HTTPS URL for *key* when ``r2_public_url`` is set.

        Args:
            key (str): Object key appended to the configured public base URL.

        Returns:
            str | None: Full URL, or ``None`` if public base URL is not
                configured (caller should proxy bytes instead).
        """
        if CONFIGURATION.r2_public_url:
            return f"{CONFIGURATION.r2_public_url.rstrip('/')}/{key}"
        return None

    def list_keys(self) -> list[str]:
        """List original image keys in the bucket (bare UUID object keys only).

        Returns:
            list[str]: Keys from paginated ``list_objects_v2`` that match
                the original UUID pattern.
        """
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket):
            for bucket_object in page.get("Contents", []):
                object_key: str = bucket_object["Key"]
                if is_original_image_key(object_key):
                    keys.append(object_key)
        return keys


_backend: FilesystemBackend | R2Backend | None = None


def get_backend() -> FilesystemBackend | R2Backend:
    """Return the process-wide image storage backend singleton.

    Returns:
        FilesystemBackend | R2Backend: Backend selected by
            ``CONFIGURATION.image_backend`` and related settings.
    """
    global _backend
    if _backend is None:
        if CONFIGURATION.image_backend == "r2":
            _backend = R2Backend()
        else:
            assert CONFIGURATION.image_directory is not None
            _backend = FilesystemBackend(CONFIGURATION.image_directory)
    return _backend


def image_file_path(key: str) -> Path | None:
    """Return a filesystem path for *key* when using the directory backend.

    Args:
        key (str): Stored object key (UUID string).

    Returns:
        Path | None: Path on disk for the filesystem backend; ``None`` for R2
            or when the object file is missing.
    """
    backend = get_backend()
    if isinstance(backend, FilesystemBackend):
        return backend.file_path(key)
    return None


def image_public_url(key: str) -> str | None:
    """Return a direct public URL for *key* when using R2 with a public base.

    Args:
        key (str): Stored object key (UUID string).

    Returns:
        str | None: Public URL from ``R2Backend.public_url``, or ``None`` when
            not applicable.
    """
    backend = get_backend()
    if isinstance(backend, R2Backend):
        return backend.public_url(key)
    return None


def load_image(key: str) -> bytes | None:
    """Load raw bytes for *key* from the active backend.

    Args:
        key (str): Stored object key.

    Returns:
        bytes | None: Object bytes, or ``None`` if missing.
    """
    return get_backend().load(key)


def sniff_image_mime(data: bytes) -> str:
    """Infer an ``image/*`` MIME type from leading magic bytes.

    Originals are stored without an extension and without metadata, so the
    filesystem and upload ``Content-Type`` are not authoritative.

    Args:
        data (bytes): Prefix of the encoded image (must include enough bytes
            for the sniff patterns).

    Returns:
        str: ``image/jpeg``, ``image/png``, etc., or
            ``application/octet-stream`` when the format is unknown so
            browsers do not mis-render bytes as an image.
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


def ensure_sized_thumbnail_on_disk(guid_str: str, w: int) -> bool:
    """Filesystem only: ensure ``{uuid}.thumb.{w}`` exists, generating from the original if needed.

    Returns:
        bool: ``True`` if the sized thumbnail exists or was created;
            ``False`` if the original image is missing on disk.
    """
    if w not in THUMBNAIL_SIZES:
        raise ValueError(f"Invalid thumbnail width {w}")
    key = thumbnail_storage_key(guid_str, w)
    backend = get_backend()
    if not isinstance(backend, FilesystemBackend):
        return True
    if backend.file_path(key) is not None:
        return True
    original_path = backend.file_path(guid_str)
    if original_path is None:
        return False
    backend.save(key, _make_thumbnail_bytes(original_path.read_bytes(), w))
    return True


def ensure_legacy_thumbnail_on_disk(guid_str: str) -> bool:
    """Filesystem only: ensure legacy ``{uuid}.thumbnail`` (256px WebP) exists.

    Returns:
        bool: ``True`` if the legacy thumbnail exists or was created;
            ``False`` if the original image is missing on disk.
    """
    key = f"{guid_str}{THUMBNAIL_SUFFIX}"
    backend = get_backend()
    if not isinstance(backend, FilesystemBackend):
        return backend.load(key) is not None
    if backend.file_path(key) is not None:
        return True
    original_path = backend.file_path(guid_str)
    if original_path is None:
        return False
    backend.save(
        key, _make_thumbnail_bytes(original_path.read_bytes(), _LEGACY_THUMB_DIM)
    )
    return True


async def save_image(file: UploadFile | Path) -> uuid.UUID:
    """Ingest an uploaded image: validate size, strip metadata, store + thumbs.

    Args:
        file (UploadFile | Path): Incoming upload or path to bytes on disk.

    Returns:
        uuid.UUID: New random UUID used as the storage key for original and
            thumbnail objects.

    Raises:
        HTTPException: 413 when the payload exceeds ``MAX_IMAGE_BYTES`` or
            Pillow raises ``DecompressionBombError`` for oversized dimensions.
    """
    data = await file.read() if isinstance(file, UploadFile) else file.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 20 MB limit")
    try:
        stripped = _strip_metadata(data)
        source = Image.open(io.BytesIO(stripped))
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=413, detail="Image dimensions too large."
        ) from exc
    file_uuid = uuid.uuid4()
    key = str(file_uuid)
    backend = get_backend()
    backend.save(key, stripped)
    for w in THUMBNAIL_SIZES:
        backend.save(
            thumbnail_storage_key(key, w), _thumbnail_webp_from_image(source, w)
        )
    return file_uuid
