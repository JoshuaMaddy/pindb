import uuid

from fastapi import UploadFile

from pindb.config import CONFIGURATION


async def save_file(file: UploadFile) -> uuid.UUID:
    file_uuid = uuid.uuid4()

    file_path = (CONFIGURATION.image_directory / f"{file_uuid}").resolve()

    file_path.write_bytes(await file.read())

    return file_uuid
