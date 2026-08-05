from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mesh_api_key: str = ""
    database_url: str = "sqlite:///./smartreco.db"
    qdrant_url: str = "http://localhost:6333"
    session_secret: str = "change-me-to-a-random-secret"
    catalog_limit: int = 1500

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    digest_from_email: str = ""

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
