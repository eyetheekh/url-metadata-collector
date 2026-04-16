from typing import Annotated, Any, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, BeforeValidator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    @staticmethod
    def parse_cors(v: Any) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list | str):
            return v
        raise ValueError(v)

    APP_NAME: str = "URL Metadata Inventory Service"
    APP_VERSION: str = "1.0.0"
    APP_VERSION_PREFIX: str = "/v1"
    DEBUG: bool = True

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyHttpUrl] | str, BeforeValidator(parse_cors)
    ] = []

    MONGODB_URL: str = "mongodb://admin:admin@localhost:27017"
    MONGODB_DB_NAME: str = "metadata_collection_db"
    MONGODB_METADATA_COLLECTION_NAME: str = "url_metadata_collection"
    MONGODB_MAXPOOL_SIZE: int = 10
    MONGODB_MINPOOL_SIZE: int = 1

    HTTP_TIMEOUT: int = 30
    HTTP_MAX_RETRIES: int = 3

    BACKGROUND_WORKER_ENABLED: bool = True

    REDIS_URL: Optional[str] = "redis://redis:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
