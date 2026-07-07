from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class ParsedResultRow:
    pilot: str
    country: str | None
    category: str | None
    quad: str | None
    time: float | None
    points: int | None
    place: int | None


@dataclass(slots=True)
class ParsedSeasonRow:
    pilot: str
    country: str | None
    category: str | None
    points: int | None
    place: int | None


@dataclass(slots=True)
class ParsedDayPayload:
    date: date
    race_class: str
    season: str
    track: str
    quad_of_the_day: str | None
    results: list[ParsedResultRow] = field(default_factory=list)
    season_leaderboard: list[ParsedSeasonRow] = field(default_factory=list)
    source: str = "unknown"
