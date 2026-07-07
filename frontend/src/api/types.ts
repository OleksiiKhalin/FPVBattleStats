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
  race_class: string;
  season: string;
  target_date: string;
  skipped_days: number;
  appearances: number;
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
  selected_pilot_consistency: ConsistencyRow | null;
  consistency_leaderboard: ConsistencyRow[];
  best_improvement: ConsistencyRow[];
};
