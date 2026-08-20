export type ScoreboardEntry = {
  place: number | null;
  pilot: string;
  country: string | null;
  category: string | null;
  quad: string | null;
  time: number | null;
  points: number | null;
};

export type ScoreboardResponse = {
  date: string;
  race_class: string;
  season: string;
  track: string;
  quad_of_the_day: string | null;
  rows: ScoreboardEntry[];
};

export type PilotOption = {
  pilot: string;
  country: string | null;
};

export type PilotTimelinePoint = {
  date: string;
  participated: boolean;
  pilot_time: number | null;
  leader_average_time: number | null;
  leader_time: number | null;
  field_average_time: number | null;
  gap_to_leader_average: number | null;
  gap_to_leader: number | null;
  normalized_score: number | null;
  place: number | null;
  participant_count: number;
};

export type PilotStatsResponse = {
  pilot: string;
  race_class: string;
  date_from: string | null;
  date_to: string | null;
  timeline: PilotTimelinePoint[];
  active_timeline: PilotTimelinePoint[];
  streaks: {
    threshold: number;
    lonely_single_days: number;
    lonely_two_day_runs: number;
    streaks: Array<{
      start_date: string;
      end_date: string;
      length: number;
      dates: string[];
    }>;
  };
};

export type PilotHoverTimelinePoint = {
  date: string;
  participated: boolean;
  place: number | null;
  skipped: number;
};

export type PilotHoverCardResponse = {
  pilot: string;
  viewpoint_pilot: string | null;
  race_class: string;
  season: string;
  target_date: string;
  skipped_days: number;
  appearances: number;
  average_place: number | null;
  season_points: number | null;
  season_wins: number;
  season_win_rate: number | null;
  shared_days_with_viewpoint: number;
  wins_against_viewpoint: number;
  win_rate_against_viewpoint: number | null;
  timeline: PilotHoverTimelinePoint[];
};

export type CountryStatsRow = {
  country: string | null;
  unique_pilots: number;
  avg_season_score: number | null;
  avg_place: number | null;
  season_wins: number;
  gold_medals: number;
  silver_medals: number;
  bronze_medals: number;
  medals_per_pilot: number | null;
};

export type QuadStatsRow = {
  quad: string;
  category: string | null;
  entries: number;
  usage_percentage: number;
  unique_pilots: number;
  avg_place: number | null;
  wins: number;
};

export type TrackRatingRow = {
  track: string;
  votes: number;
  average_score: number;
  weighted_score: number;
};

export type SeasonStatsRow = {
  season: string;
  unique_pilots: number;
  consistent_pilots: number;
  largest_victory_margin: number | null;
};

export type ParticipationDayRow = {
  date: string;
  participants: number;
};

export type EasyDayRow = {
  date: string;
  average_gap_to_leader: number | null;
  average_gap_percentage: number | null;
  participant_count: number;
  is_favorable: boolean | null;
};

export type ConsistencyRow = {
  pilot: string;
  country: string | null;
  appearances: number;
  average_place: number | null;
  dispersion: number;
  consistency_score: number;
  first_flight_date: string;
  last_flight_date: string;
  improvement_score: number | null;
};

export type GeneralStatsResponse = {
  race_class: string;
  date_from: string | null;
  date_to: string | null;
  selected_pilot: string | null;
  countries: CountryStatsRow[];
  quads: QuadStatsRow[];
  track_ratings: TrackRatingRow[];
  seasons: SeasonStatsRow[];
  participation: {
    daily_counts: ParticipationDayRow[];
    average_participants: number;
    peak_participation_day: ParticipationDayRow | null;
    lowest_participation_day: ParticipationDayRow | null;
    participation_trend: number | null;
  };
  easy_days: {
    consistent_pilots_only: boolean;
    regular_pilot_threshold: number;
    eligible_pilot_count: number;
    period_average_gap_to_leader: number | null;
    period_average_gap_percentage: number | null;
    selected_day: EasyDayRow | null;
    favorable_days: number;
    daily_gaps: EasyDayRow[];
  };
  selected_pilot_consistency: ConsistencyRow | null;
  consistency_leaderboard: ConsistencyRow[];
  best_improvement: ConsistencyRow[];
};

export type GlobalLeaderboardForecast = {
  checkpoint_date: string;
  no_flight_days: number;
  continue_flight_days: number;
  no_flight_adjusted_average_gap: number | null;
  continue_adjusted_average_gap: number | null;
  no_flight_rank: number | null;
  no_flight_league: string | null;
  continue_rank: number | null;
  continue_league: string | null;
  days_needed_to_qualify: number;
  can_qualify_if_active: boolean;
};

export type GlobalLeaderboardRow = {
  pilot: string;
  country: string | null;
  rank: number | null;
  league: string | null;
  status: "qualified" | "at_risk" | "guaranteed_out" | "candidate";
  status_reason: string;
  flight_days: number;
  scored_days: number;
  last_flight_date: string | null;
  inactive_days: number;
  adjusted_average_gap: number | null;
  worst_day_gap: number | null;
  target_league: string | null;
  gap_to_next_league: number | null;
  required_flight_days: number;
  rank_delta: number | null;
  league_delta: "up" | "down" | null;
  forecast_weekly: GlobalLeaderboardForecast;
  forecast_monthly: GlobalLeaderboardForecast;
};

export type GlobalLeaderboardResponse = {
  race_class: string;
  as_of_date: string;
  window_from: string;
  window_to: string;
  last_official_snapshot_date: string | null;
  last_official_snapshot_kind: string | null;
  next_weekly_checkpoint: string;
  next_month_start: string;
  minimum_flight_days: number;
  window_days: number;
  gold_places: number;
  silver_places: number;
  selected_pilot: GlobalLeaderboardRow | null;
  rows: GlobalLeaderboardRow[];
};


export type PilotComparisonPilotStats = {
  flights: number;
  longest_streak: number;
  average_gap_to_leader: number | null;
  total_score: number;
  average_place_by_category: Record<string, number | null>;
};

export type PilotComparisonDay = {
  date: string;
  primary_time: number | null;
  opponent_time: number | null;
  difference_seconds: number | null;
  difference_percent: number | null;
  primary_gap_to_leader: number | null;
  opponent_gap_to_leader: number | null;
  primary_place: number | null;
  opponent_place: number | null;
};

export type PilotComparisonResponse = {
  primary_pilot: string;
  opponent_pilot: string;
  race_class: string;
  date_from: string | null;
  date_to: string | null;
  season: string | null;
  seasons: string[];
  shared_days: number;
  primary_wins: number;
  win_rate: number | null;
  primary: PilotComparisonPilotStats;
  opponent: PilotComparisonPilotStats;
  days: PilotComparisonDay[];
};
