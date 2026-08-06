from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mesh_api_key: str = ""
    database_url: str = "sqlite:///./smartreco.db"
    qdrant_url: str = "http://localhost:6333"
    session_secret: str = "change-me-to-a-random-secret"
    catalog_limit: int = 1500

    # Used to build absolute links in the digest email (dashboard/course
    # links) - emails are opened outside any browser session tied to the
    # app's own host, so relative URLs won't work there like they do in
    # server-rendered pages.
    public_base_url: str = "http://localhost:8000"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    digest_from_email: str = ""

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "smartreco"


@lru_cache
def get_settings() -> Settings:
    return Settings()
