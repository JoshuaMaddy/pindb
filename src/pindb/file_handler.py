import uuid
from math import floor

from fastapi import UploadFile
from PIL import Image

from pindb.config import CONFIGURATION


async def save_file(file: UploadFile) -> uuid.UUID:
    file_uuid = uuid.uuid4()

    file_path = (CONFIGURATION.image_directory / str(file_uuid)).resolve()

    file_path.write_bytes(await file.read())

    return file_uuid


async def create_thumbnail(file_uuid: str) -> None:
    file_path = (CONFIGURATION.image_directory / file_uuid).resolve()

    if not file_path.exists() or not file_path.is_file():
        raise ValueError("No file!")

    image = Image.open(file_path)

    aspect_ratio = image.width / image.height
    if aspect_ratio >= 1:
        new_width = 256
        new_height = 256 // aspect_ratio
    else:
        new_width = floor(256 * aspect_ratio)
        new_height = 256

    new_image = image.resize((int(new_width), int(new_height)))
    new_image.save(file_path.with_name(name=f"{file_uuid}.thumbnail"), format="webp")
