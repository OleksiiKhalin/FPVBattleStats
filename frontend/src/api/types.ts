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

export type GapPoint = {
  date: string;
  pilot_time: number | null;
  leader_average_time: number | null;
  field_average_time: number | null;
  gap_to_leader_average: number | null;
};

export type PilotAnalyticsResponse = {
  pilot: string;
  race_class: string;
  season: string | null;
  points_timeline: GapPoint[];
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

export type CountryStatsRow = {
  country: string | null;
  unique_pilots: number;
  avg_season_score: number | null;
  avg_place: number | null;
  season_wins: number;
  gold_medals: number;
  silver_medals: number;
  bronze_medals: number;
};
