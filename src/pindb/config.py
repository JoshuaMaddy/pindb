from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    image_directory: Path
    database_connection: str


CONFIGURATION = Configuration()  # type: ignore
