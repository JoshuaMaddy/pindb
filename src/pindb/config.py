from pathlib import Path

import meilisearch
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Images
    image_directory: Path

    # Postgres
    database_connection: str

    # Meilisearch
    meilisearch_key: str
    meilisearch_url: str = Field(default="http://127.0.0.1:7700")
    meilisearch_index: str = Field(default="pins")

    __meili_client: meilisearch.Client | None = None  # type: ignore

    @property
    def meili_client(self) -> meilisearch.Client:
        if self.__meili_client is None:
            self.__meili_client = meilisearch.Client(
                url=self.meilisearch_url,
                api_key=self.meilisearch_key,
            )

        return self.__meili_client

    # Logging
    logging_date_format: str = Field(default="%d %b %Y | %H:%M:%S")
    logging_format: str = Field(default="%(asctime)s | %(name)s | %(message)s")
    log_file: str = Field(default="pindb.log")


CONFIGURATION = Configuration()  # type: ignore
