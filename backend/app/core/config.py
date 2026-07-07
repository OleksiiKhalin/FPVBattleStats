from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPVBATTLE_", env_file=".env", extra="ignore")

    app_name: str = "FPVBattle Stats API"
    api_prefix: str = "/api"
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[3] / 'data' / 'fpvbattle.db'}",
    )
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()

