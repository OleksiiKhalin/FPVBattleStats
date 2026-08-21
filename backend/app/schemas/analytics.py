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


class PilotComparisonPilotStats(BaseModel):
    flights: int
    longest_streak: int
    average_gap_to_leader: float | None = None
    total_score: int
    average_place_by_category: dict[str, float | None]


class PilotComparisonDay(BaseModel):
    date: date
    primary_time: float | None = None
    opponent_time: float | None = None
    difference_seconds: float | None = None
    difference_percent: float | None = None
    primary_gap_to_leader: float | None = None
    opponent_gap_to_leader: float | None = None
    primary_gap_to_leader_percentage: float | None = None
    opponent_gap_to_leader_percentage: float | None = None
    primary_place: int | None = None
    opponent_place: int | None = None


class PilotComparisonResponse(BaseModel):
    primary_pilot: str
    opponent_pilot: str
    race_class: str
    date_from: date | None = None
    date_to: date | None = None
    season: str | None = None
    seasons: list[str]
    shared_days: int
    primary_wins: int
    win_rate: float | None = None
    primary: PilotComparisonPilotStats
    opponent: PilotComparisonPilotStats
    days: list[PilotComparisonDay]


class PilotHoverTimelinePoint(BaseModel):
    date: date
    participated: bool
    place: int | None = None
    skipped: int


class PilotHoverCardResponse(BaseModel):
    pilot: str
    viewpoint_pilot: str | None = None
    race_class: str
    season: str
    target_date: date
    skipped_days: int
    appearances: int
    average_place: float | None = None
    season_points: int | None = None
    season_wins: int
    season_win_rate: float | None = None
    shared_days_with_viewpoint: int
    wins_against_viewpoint: int
    win_rate_against_viewpoint: float | None = None
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


class EasyDayRow(BaseModel):
    date: date
    average_gap_to_leader: float | None = None
    average_gap_percentage: float | None = None
    participant_count: int
    is_favorable: bool | None = None


class EasyDaysStats(BaseModel):
    consistent_pilots_only: bool
    regular_pilot_threshold: int
    eligible_pilot_count: int
    period_average_gap_to_leader: float | None = None
    period_average_gap_percentage: float | None = None
    selected_day: EasyDayRow | None = None
    favorable_days: int
    daily_gaps: list[EasyDayRow]


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
    easy_days: EasyDaysStats
    selected_pilot_consistency: ConsistencyRow | None = None
    consistency_leaderboard: list[ConsistencyRow]
    best_improvement: list[ConsistencyRow]


class GlobalLeaderboardForecast(BaseModel):
    checkpoint_date: date
    no_flight_days: int
    continue_flight_days: int
    no_flight_adjusted_average_gap_percentage: float | None = None
    continue_adjusted_average_gap_percentage: float | None = None
    no_flight_rank: int | None = None
    no_flight_league: str | None = None
    continue_rank: int | None = None
    continue_league: str | None = None
    days_needed_to_qualify: int
    can_qualify_if_active: bool


class GlobalLeaderboardRow(BaseModel):
    pilot: str
    country: str | None = None
    display_rank: int | None = None
    display_league: str | None = None
    current_league: str
    rank: int | None = None
    league: str | None = None
    status: str
    status_reason: str
    flight_days: int
    scored_days: int
    first_flight_date: date | None = None
    last_flight_date: date | None = None
    inactive_days: int
    season_missed_days: int
    missed_last_7_days: int
    missed_last_15_days: int
    adjusted_average_gap_percentage: float | None = None
    current_gap_percentage: float | None = None
    gap_change_percentage: float | None = None
    change_reference_gap_percentage: float | None = None
    worst_day_gap_percentage: float | None = None
    target_league: str | None = None
    gap_to_next_league_percentage: float | None = None
    required_flight_days: int
    days_needed_for_next_season: int
    available_days_before_next_season: int
    next_season_retained_days: int
    can_pass_next_season: bool
    season_start_rank: int | None = None
    season_start_league: str | None = None
    season_start_snapshot_date: date | None = None
    projected_next_season_rank: int | None = None
    projected_next_season_league: str | None = None
    projected_next_season_eligible: bool
    smart_sort_bucket: int
    rank_delta: int | None = None
    league_delta: str | None = None
    forecast_weekly: GlobalLeaderboardForecast
    forecast_monthly: GlobalLeaderboardForecast


class GlobalLeaderboardResponse(BaseModel):
    race_class: str
    view_mode: str
    as_of_date: date
    latest_data_date: date | None = None
    is_historical: bool
    window_from: date
    window_to: date
    last_official_snapshot_date: date | None = None
    last_official_snapshot_kind: str | None = None
    season_start_snapshot_date: date | None = None
    change_reference_date: date | None = None
    change_reference_kind: str | None = None
    next_weekly_checkpoint: date
    next_month_start: date
    season_end_date: date
    minimum_flight_days: int
    window_days: int
    gold_places: int
    silver_places: int
    selected_pilot: GlobalLeaderboardRow | None = None
    rows: list[GlobalLeaderboardRow]
