from datetime import date

from pydantic import BaseModel


class DayRef(BaseModel):
    date: date
    race_class: str
    season: str


class PilotSummary(BaseModel):
    pilot: str
    country: str | None = None

