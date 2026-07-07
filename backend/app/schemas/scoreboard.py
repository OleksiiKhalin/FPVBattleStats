from datetime import date

from pydantic import BaseModel


class ScoreboardEntry(BaseModel):
    place: int | None = None
    pilot: str
    country: str | None = None
    category: str | None = None
    quad: str | None = None
    time: float | None = None
    points: int | None = None


class ScoreboardResponse(BaseModel):
    date: date
    race_class: str
    season: str
    track: str
    quad_of_the_day: str | None = None
    rows: list[ScoreboardEntry]

