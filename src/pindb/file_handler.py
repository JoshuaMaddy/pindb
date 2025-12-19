import uuid
from math import floor
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from PIL.ImageFile import ImageFile

from pindb.config import CONFIGURATION


async def save_file(file: UploadFile) -> uuid.UUID:
    file_uuid: uuid.UUID = uuid.uuid4()

    file_path: Path = (CONFIGURATION.image_directory / str(file_uuid)).resolve()

    file_path.write_bytes(data=await file.read())

    return file_uuid


async def create_thumbnail(file_uuid: str) -> None:
    file_path: Path = (CONFIGURATION.image_directory / file_uuid).resolve()

    if not file_path.exists() or not file_path.is_file():
        raise ValueError("No file!")

    image: ImageFile = Image.open(fp=file_path)

    aspect_ratio = image.width / image.height
    if aspect_ratio >= 1:
        new_width = 256
        new_height: int | float = 256 // aspect_ratio
    else:
        new_width: int = floor(256 * aspect_ratio)
        new_height = 256

    new_image = image.resize(size=(int(new_width), int(new_height)))
    new_image.save(file_path.with_name(name=f"{file_uuid}.thumbnail"), format="webp")
