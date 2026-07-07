from datetime import date
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScraperSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FPVBATTLE_", env_file=".env", extra="ignore")

    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[3] / 'data' / 'fpvbattle.db'}",
    )
    open_base_url: str = "https://ua-velocidrone.fun"
    whoop_base_url: str = "https://ua-velocidrone.fun/whoop"
    api_base_url: str = "https://ua-velocidrone.fun"
    historical_start_date: date = date(2023, 11, 15)
    request_timeout_seconds: float = 30.0
    request_delay_seconds: float = 2.0
    request_jitter_seconds: float = 0.5
    request_max_retries: int = 3
    request_backoff_seconds: float = 2.0
    dump_failed_pages: bool = True


settings = ScraperSettings()
