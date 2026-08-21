import { useEffect, useMemo, useState } from "react";

import type { GlobalLeaderboardResponse, GlobalLeaderboardRow } from "../api/types";

type Props = {
  data: GlobalLeaderboardResponse;
  selectedPilot: string;
  onDateChange: (value: string) => void;
  onViewModeChange: (value: "current" | "probable") => void;
};

type ForecastMode = "weekly" | "monthly";
type SortDirection = "asc" | "desc";
type SortKey =
  | "season_start_rank"
  | "rank"
  | "projected_next_season_rank"
  | "pilot"
  | "current_league"
  | "flight_days"
  | "days_needed_for_next_season"
  | "inactive_days"
  | "season_missed_days"
  | "adjusted_average_gap_percentage"
  | "current_gap_percentage"
  | "gap_change_percentage"
  | "projected_next_season_league"
  | "status";

const leagueOrder: Record<string, number> = { gold: 1, silver: 2, bronze: 3, candidate: 4, unranked: 5 };

function leagueLabel(league: string | null) {
  if (!league) return "Unranked";
  return league[0].toUpperCase() + league.slice(1);
}

function rankLabel(rank: number | null) {
  return rank ? `#${rank}` : "-";
}

function percentLabel(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function gapChangeLabel(value: number | null) {
  if (value === null || value === 0) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function valueFor(row: GlobalLeaderboardRow, key: SortKey): string | number | null {
  if (key === "current_league" || key === "projected_next_season_league") {
    const value = key === "current_league" ? row.current_league : row.projected_next_season_league;
    return value ? leagueOrder[value] ?? 99 : 99;
  }
  return row[key];
}

function compareRows(left: GlobalLeaderboardRow, right: GlobalLeaderboardRow, key: SortKey, direction: SortDirection) {
  if (key === "current_league" || key === "projected_next_season_league") {
    const leftLeague = Number(valueFor(left, key));
    const rightLeague = Number(valueFor(right, key));
    const leftRank = key === "current_league" ? left.rank : left.projected_next_season_rank;
    const rightRank = key === "current_league" ? right.rank : right.projected_next_season_rank;
    const leagueResult = leftLeague - rightLeague;
    const rankResult = (leftRank ?? Number.POSITIVE_INFINITY) - (rightRank ?? Number.POSITIVE_INFINITY);
    return (leagueResult || rankResult || left.pilot.localeCompare(right.pilot)) * (direction === "asc" ? 1 : -1);
  }
  const leftValue = valueFor(left, key);
  const rightValue = valueFor(right, key);
  if (leftValue === null && rightValue === null) return left.pilot.localeCompare(right.pilot);
  if (leftValue === null) return 1;
  if (rightValue === null) return -1;
  const result = typeof leftValue === "string" && typeof rightValue === "string"
    ? leftValue.localeCompare(rightValue)
    : Number(leftValue) - Number(rightValue);
  return (result || left.pilot.localeCompare(right.pilot)) * (direction === "asc" ? 1 : -1);
}

function leagueClass(league: string | null) {
  return `league-pill league-${league ?? "candidate"}`;
}

export function GlobalLeaderboardPanel({ data, selectedPilot, onDateChange, onViewModeChange }: Props) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [leagueFilter, setLeagueFilter] = useState("all");
  const [forecastMode, setForecastMode] = useState<ForecastMode>("monthly");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  useEffect(() => {
    setSortKey(data.view_mode === "probable" ? "projected_next_season_rank" : "rank");
    setSortDirection("asc");
  }, [data.view_mode]);

  const filteredRows = useMemo(() => data.rows.filter((row) => {
    const visibleLeague = data.view_mode === "probable" ? row.display_league : row.current_league;
    return (statusFilter === "all" || row.status === statusFilter)
      && (leagueFilter === "all" || visibleLeague === leagueFilter);
  }), [data.rows, data.view_mode, leagueFilter, statusFilter]);

  const rows = useMemo(
    () => [...filteredRows].sort((left, right) => compareRows(left, right, sortKey, sortDirection)),
    [filteredRows, sortDirection, sortKey],
  );
  const focus = data.selected_pilot ?? data.rows.find((row) => row.pilot === selectedPilot) ?? null;
  const forecast = focus ? focus[forecastMode === "weekly" ? "forecast_weekly" : "forecast_monthly"] : null;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((value) => value === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const sortButton = (key: SortKey, label: string) => (
    <button
      type="button"
      className="table-sort-button"
      onClick={() => handleSort(key)}
      aria-label={`Sort by ${label}`}
      aria-sort={sortKey === key ? sortDirection === "asc" ? "ascending" : "descending" : "none"}
    >
      {label}{sortKey === key ? (sortDirection === "asc" ? " ^" : " v") : ""}
    </button>
  );

  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Global leaderboard</p>
            <h2>{selectedPilot} outlook</h2>
          </div>
          <div className="meta">
            <span>{data.window_from} to {data.window_to}</span>
            <span>Season start: {data.season_start_snapshot_date ?? "not available"}</span>
            <span>Change reference: {data.change_reference_date ?? "not available"}</span>
          </div>
        </div>
        {focus ? (
          <>
            <div className="stat-grid global-leaderboard-kpis">
              <div className="stat-card"><span>Season start rank</span><strong>{rankLabel(focus.season_start_rank)}</strong></div>
              <div className="stat-card"><span>Current rank</span><strong>{leagueLabel(focus.league)} {rankLabel(focus.rank)}</strong></div>
              <div className="stat-card"><span>Projected next month</span><strong>{leagueLabel(focus.projected_next_season_league)} {rankLabel(focus.projected_next_season_rank)}</strong></div>
              <div className="stat-card"><span>Flight-days / 30</span><strong>{focus.flight_days} / {data.window_days}</strong></div>
              <div className="stat-card"><span>Gap to top 3 (%)</span><strong>{percentLabel(focus.adjusted_average_gap_percentage)}</strong></div>
              <div className="stat-card"><span>Need / remain</span><strong>{focus.days_needed_for_next_season} / {focus.available_days_before_next_season}</strong></div>
            </div>
            <p className="chart-note">{focus.status_reason}</p>
            {forecast ? (
              <div className="forecast-strip">
                <div className="toggle-row">
                  <button type="button" className={forecastMode === "weekly" ? "chip active" : "chip"} onClick={() => setForecastMode("weekly")}>Next Monday</button>
                  <button type="button" className={forecastMode === "monthly" ? "chip active" : "chip"} onClick={() => setForecastMode("monthly")}>Next month</button>
                </div>
                <span>Without flying: {forecast.no_flight_days} days</span>
                <span>If flying: {forecast.continue_flight_days} days</span>
                <span>Projected gap: {percentLabel(forecast.continue_adjusted_average_gap_percentage)}</span>
              </div>
            ) : null}
            <div className="leaderboard-context">
              <label className="date-selector">
                <span>Leaderboard date</span>
                <input type="date" value={data.as_of_date} max={data.latest_data_date ?? undefined} onChange={(event) => onDateChange(event.target.value)} />
              </label>
              {data.is_historical ? (
                <p className="history-note">Historical slice: results after {data.as_of_date} are excluded. Current gap is shown only as a reference and does not affect this ranking.</p>
              ) : null}
            </div>
          </>
        ) : (
          <>
            <p>No active results in the selected 30-day window.</p>
            <div className="leaderboard-context">
              <label className="date-selector">
                <span>Leaderboard date</span>
                <input type="date" value={data.as_of_date} max={data.latest_data_date ?? undefined} onChange={(event) => onDateChange(event.target.value)} />
              </label>
              {data.is_historical ? <p className="history-note">Historical slice: results after {data.as_of_date} are excluded. Current gap is shown only as a reference and does not affect this ranking.</p> : null}
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">{data.view_mode === "probable" ? "Probable next-month field" : "Current field"}</p>
            <h2>{data.view_mode === "probable" ? "Projected leaderboard" : "Active pilots and next-season risk"}</h2>
          </div>
          <div className="toggle-row leaderboard-filters">
            <button
              type="button"
              className={data.view_mode === "probable" ? "chip active" : "chip"}
              disabled={data.is_historical}
              onClick={() => onViewModeChange(data.view_mode === "probable" ? "current" : "probable")}
            >
              {data.view_mode === "probable" ? "Show current leaderboard" : "Show probable next month"}
            </button>
            <label>Status <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All</option><option value="qualified">Qualified</option><option value="at_risk">At risk</option><option value="candidate">Candidate</option><option value="guaranteed_out">Guaranteed out</option></select></label>
            <label>League <select value={leagueFilter} onChange={(event) => setLeagueFilter(event.target.value)}><option value="all">All</option><option value="gold">Gold</option><option value="silver">Silver</option><option value="bronze">Bronze</option><option value="unranked">Unranked</option></select></label>
          </div>
        </div>
        <div className="table-scroll">
          <table className="scoreboard compact-scoreboard global-leaderboard-table">
            <thead><tr>
              <th>{sortButton("season_start_rank", "Start")}</th>
              <th>{sortButton("rank", "Current")}</th>
              <th>{sortButton("projected_next_season_rank", "Projected")}</th>
              <th>{sortButton("pilot", "Pilot")}</th>
              <th>{sortButton("current_league", "Current league")}</th>
              <th>{sortButton("projected_next_season_league", "Projected league")}</th>
              <th>{sortButton("flight_days", "Days")}</th>
              <th>{sortButton("days_needed_for_next_season", "Need / remain")}</th>
              <th>{sortButton("inactive_days", "Inactive")}</th>
              <th>{sortButton("adjusted_average_gap_percentage", "Gap")}</th>
              {data.is_historical ? <th>{sortButton("current_gap_percentage", "Current gap")}</th> : null}
              <th>{sortButton("gap_change_percentage", "Change")}</th>
              <th>{sortButton("status", "Outlook")}</th>
            </tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row.pilot} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                <td>{rankLabel(row.season_start_rank)}</td>
                <td>{rankLabel(row.rank)}</td>
                <td>{rankLabel(row.projected_next_season_rank)}</td>
                <td><strong>{row.pilot}</strong>{row.country ? <small className="table-muted"> {row.country}</small> : null}<small className="table-muted">First flight: {row.first_flight_date ?? "-"}</small></td>
                <td><span className={leagueClass(row.current_league)}>{leagueLabel(row.current_league)}</span></td>
                <td><span className={leagueClass(row.projected_next_season_league)}>{leagueLabel(row.projected_next_season_league)}</span></td>
                <td>{row.flight_days}/{data.window_days}<small className="table-muted">{row.scored_days} scored</small></td>
                <td>{row.days_needed_for_next_season} / {row.available_days_before_next_season}<small className="table-muted">{row.can_pass_next_season ? "can pass" : "not enough days"}</small></td>
                <td>{row.inactive_days}<small className="table-muted">days since last flight</small><small className="table-muted">missed last 7d: {row.missed_last_7_days}</small><small className="table-muted">missed last 15d: {row.missed_last_15_days}</small></td>
                <td>{percentLabel(row.adjusted_average_gap_percentage)}</td>
                {data.is_historical ? <td>{percentLabel(row.current_gap_percentage)}</td> : null}
                <td>{gapChangeLabel(row.gap_change_percentage)}<small className="table-muted">vs {data.change_reference_date ?? "-"}</small></td>
                <td><span className={`status-pill status-${row.status}`}>{row.status.replace("_", " ")}</span><small className="table-reason">{row.status_reason}</small></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="chart-note">Click any column heading to sort. `Need / remain` shows extra flight-days needed before the next month and available days left in the current season. Inactive is days since the last flight; season missed is a separate count from the pilot's first flight in this season.</p>
      </section>
    </div>
  );
}
