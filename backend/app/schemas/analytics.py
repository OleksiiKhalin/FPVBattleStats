from datetime import date

from pydantic import BaseModel


class PilotOption(BaseModel):
    pilot: str
    country: str | None = None


class PilotTimelinePoint(BaseModel):
    date: date
    participated: bool
    pilot_time: float | None = None
    leader_average_time: float | None = None
    leader_time: float | None = None
    field_average_time: float | None = None
    gap_to_leader_average: float | None = None
    gap_to_leader: float | None = None
    normalized_score: float | None = None
    place: int | None = None
    participant_count: int


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


class PilotStatsResponse(BaseModel):
    pilot: str
    race_class: str
    date_from: date | None = None
    date_to: date | None = None
    timeline: list[PilotTimelinePoint]
    active_timeline: list[PilotTimelinePoint]
    streaks: PilotStreakSummary


class PilotHoverTimelinePoint(BaseModel):
    date: date
    participated: bool
    place: int | None = None
    skipped: int


class PilotHoverCardResponse(BaseModel):
    pilot: str
    race_class: str
    season: str
    target_date: date
    skipped_days: int
    appearances: int
    timeline: list[PilotHoverTimelinePoint]


class CountryStatsRow(BaseModel):
    country: str | None = None
    unique_pilots: int
    avg_season_score: float | None = None
    avg_place: float | None = None
    season_wins: int
    gold_medals: int
    silver_medals: int
    bronze_medals: int
    medals_per_pilot: float | None = None


class QuadStatsRow(BaseModel):
    quad: str
    category: str | None = None
    entries: int
    usage_percentage: float
    unique_pilots: int
    avg_place: float | None = None
    wins: int


class TrackRatingRow(BaseModel):
    track: str
    votes: int
    average_score: float
    weighted_score: float


class SeasonStatsRow(BaseModel):
    season: str
    unique_pilots: int
    consistent_pilots: int
    largest_victory_margin: float | None = None


class ParticipationDayRow(BaseModel):
    date: date
    participants: int


class ParticipationStats(BaseModel):
    daily_counts: list[ParticipationDayRow]
    average_participants: float
    peak_participation_day: ParticipationDayRow | None = None
    lowest_participation_day: ParticipationDayRow | None = None
    participation_trend: float | None = None


class ConsistencyRow(BaseModel):
    pilot: str
    country: str | None = None
    appearances: int
    average_place: float | None = None
    dispersion: float
    consistency_score: float
    first_flight_date: date
    last_flight_date: date
    improvement_score: float | None = None


class GeneralStatsResponse(BaseModel):
    race_class: str
    date_from: date | None = None
    date_to: date | None = None
    selected_pilot: str | None = None
    countries: list[CountryStatsRow]
    quads: list[QuadStatsRow]
    track_ratings: list[TrackRatingRow]
    seasons: list[SeasonStatsRow]
    participation: ParticipationStats
    selected_pilot_consistency: ConsistencyRow | None = None
    consistency_leaderboard: list[ConsistencyRow]
    best_improvement: list[ConsistencyRow]
