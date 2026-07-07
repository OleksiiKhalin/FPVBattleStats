from pathlib import Path

import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPVBATTLE_", env_file=".env", extra="ignore")

    app_name: str = "FPVBattle Stats API"
    api_prefix: str = "/api"
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[3] / 'data' / 'fpvbattle.db'}",
    )
    cors_origins: str = "http://localhost:5173"

    def get_cors_origins(self) -> list[str]:
        stripped = self.cors_origins.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            raise ValueError("FPVBATTLE_CORS_ORIGINS JSON value must be an array.")
        return [item.strip() for item in stripped.split(",") if item.strip()]


settings = Settings()
