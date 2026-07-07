from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPVBATTLE_", env_file=".env", extra="ignore")

    app_name: str = "FPVBattle Stats API"
    api_prefix: str = "/api"
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[3] / 'data' / 'fpvbattle.db'}",
    )
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


settings = Settings()
