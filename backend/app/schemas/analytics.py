from datetime import date

from pydantic import BaseModel


class GapPoint(BaseModel):
    date: date
    pilot_time: float | None = None
    leader_average_time: float | None = None
    field_average_time: float | None = None
    gap_to_leader_average: float | None = None


class CountryStatsRow(BaseModel):
    country: str | None = None
    unique_pilots: int
    avg_season_score: float | None = None
    avg_place: float | None = None
    season_wins: int
    gold_medals: int
    silver_medals: int
    bronze_medals: int


class PilotStreakGroup(BaseModel):
    start_date: date
    end_date: date
    length: int
    dates: list[date]


class PilotStreakSummary(BaseModel):
    threshold: int
    streaks: list[PilotStreakGroup]
    lonely_single_days: int
    lonely_two_day_runs: int


class PilotAnalyticsResponse(BaseModel):
    pilot: str
    race_class: str
    season: str | None = None
    points_timeline: list[GapPoint]
    streaks: PilotStreakSummary

