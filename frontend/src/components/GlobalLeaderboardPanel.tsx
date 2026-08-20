import { useMemo, useState } from "react";

import type { GlobalLeaderboardResponse, GlobalLeaderboardRow } from "../api/types";

type Props = {
  data: GlobalLeaderboardResponse;
  selectedPilot: string;
};

type ForecastMode = "weekly" | "monthly";
type SortMode = "official" | "smart";

function leagueLabel(league: string | null) {
  if (!league) return "Candidate";
  return league[0].toUpperCase() + league.slice(1);
}

function rankLabel(rank: number | null) {
  return rank ? `#${rank}` : "—";
}

function percentLabel(value: number | null) {
  return value === null ? "—" : `${value.toFixed(2)}%`;
}

function deltaLabel(row: GlobalLeaderboardRow) {
  if (row.rank_delta === null || row.rank_delta === 0) return "—";
  return row.rank_delta > 0 ? `↑ ${row.rank_delta}` : `↓ ${Math.abs(row.rank_delta)}`;
}

function sortSmart(rows: GlobalLeaderboardRow[]) {
  return [...rows].sort((left, right) => (
    left.smart_sort_bucket - right.smart_sort_bucket
    || left.days_needed_for_next_season - right.days_needed_for_next_season
    || (left.projected_next_season_rank ?? Number.POSITIVE_INFINITY) - (right.projected_next_season_rank ?? Number.POSITIVE_INFINITY)
    || (left.adjusted_average_gap_percentage ?? Number.POSITIVE_INFINITY) - (right.adjusted_average_gap_percentage ?? Number.POSITIVE_INFINITY)
    || left.pilot.localeCompare(right.pilot)
  ));
}

export function GlobalLeaderboardPanel({ data, selectedPilot }: Props) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [leagueFilter, setLeagueFilter] = useState("all");
  const [forecastMode, setForecastMode] = useState<ForecastMode>("monthly");
  const [sortMode, setSortMode] = useState<SortMode>("official");
  const filteredRows = useMemo(() => data.rows.filter((row) => (
    (statusFilter === "all" || row.status === statusFilter)
    && (leagueFilter === "all" || row.league === leagueFilter)
  )), [data.rows, leagueFilter, statusFilter]);
  const rows = useMemo(
    () => sortMode === "smart" ? sortSmart(filteredRows) : filteredRows,
    [filteredRows, sortMode],
  );
  const focus = data.selected_pilot ?? data.rows.find((row) => row.pilot === selectedPilot) ?? null;
  const forecast = focus ? focus[forecastMode === "weekly" ? "forecast_weekly" : "forecast_monthly"] : null;

  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Global leaderboard</p>
            <h2>{selectedPilot} outlook</h2>
          </div>
          <div className="meta">
            <span>{data.window_from} → {data.window_to}</span>
            <span>Season-start snapshot: {data.season_start_snapshot_date ?? "not available"}</span>
          </div>
        </div>
        {focus ? (
          <>
            <div className="stat-grid global-leaderboard-kpis">
              <div className="stat-card"><span>Season start rank</span><strong>{rankLabel(focus.season_start_rank)}</strong></div>
              <div className="stat-card"><span>Current rank</span><strong>{leagueLabel(focus.league)} {rankLabel(focus.rank)}</strong></div>
              <div className="stat-card"><span>Projected next season</span><strong>{leagueLabel(focus.projected_next_season_league)} {rankLabel(focus.projected_next_season_rank)}</strong></div>
              <div className="stat-card"><span>Flight-days / 30</span><strong>{focus.flight_days} / {data.window_days}</strong></div>
              <div className="stat-card"><span>Gap to leader</span><strong>{percentLabel(focus.adjusted_average_gap_percentage)}</strong></div>
              <div className="stat-card"><span>Days needed to stay</span><strong>{focus.days_needed_for_next_season} / {focus.available_days_before_next_season}</strong></div>
            </div>
            <p className="chart-note">{focus.status_reason}</p>
            {forecast ? (
              <div className="forecast-strip">
                <div className="toggle-row">
                  <button type="button" className={forecastMode === "weekly" ? "chip active" : "chip"} onClick={() => setForecastMode("weekly")}>Next Monday</button>
                  <button type="button" className={forecastMode === "monthly" ? "chip active" : "chip"} onClick={() => setForecastMode("monthly")}>Next season</button>
                </div>
                <span>Without flying: {forecast.no_flight_days} days</span>
                <span>If flying: {forecast.continue_flight_days} days</span>
                <span>Projected gap: {percentLabel(forecast.continue_adjusted_average_gap_percentage)}</span>
              </div>
            ) : null}
          </>
        ) : <p>No active results in the current 30-day window.</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Current field</p>
            <h2>Active pilots and next-season risk</h2>
          </div>
          <div className="toggle-row leaderboard-filters">
            <button type="button" className={sortMode === "smart" ? "chip active" : "chip"} onClick={() => setSortMode((value) => value === "smart" ? "official" : "smart")}>Sort by chances / risk</button>
            <label>Status <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All</option><option value="qualified">Qualified</option><option value="at_risk">At risk</option><option value="candidate">Candidate</option><option value="guaranteed_out">Guaranteed out</option></select></label>
            <label>League <select value={leagueFilter} onChange={(event) => setLeagueFilter(event.target.value)}><option value="all">All</option><option value="gold">Gold</option><option value="silver">Silver</option><option value="bronze">Bronze</option></select></label>
          </div>
        </div>
        <div className="table-scroll">
          <table className="scoreboard compact-scoreboard global-leaderboard-table">
            <thead><tr><th>Start</th><th>Current</th><th>Next season</th><th>Pilot</th><th>League</th><th>Days</th><th>Need / remain</th><th>Gap</th><th>Inactive</th><th>Change</th><th>Outlook</th></tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row.pilot} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                <td>{rankLabel(row.season_start_rank)}</td>
                <td>{rankLabel(row.rank)}</td>
                <td>{rankLabel(row.projected_next_season_rank)}</td>
                <td><strong>{row.pilot}</strong>{row.country ? <small className="table-muted"> {row.country}</small> : null}</td>
                <td><span className={`league-pill league-${row.league ?? "candidate"}`}>{leagueLabel(row.league)}</span></td>
                <td>{row.flight_days}/{data.window_days}</td>
                <td>{row.days_needed_for_next_season} / {row.available_days_before_next_season}<small className="table-muted">{row.can_pass_next_season ? "can pass" : "not enough days"}</small></td>
                <td>{percentLabel(row.adjusted_average_gap_percentage)}</td>
                <td>{row.inactive_days}</td>
                <td>{deltaLabel(row)}</td>
                <td><span className={`status-pill status-${row.status}`}>{row.status.replace("_", " ")}</span><small className="table-reason">{row.status_reason}</small></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="chart-note">Gap is the adjusted average percentage behind the daily top-three average, excluding one worst day. “Need / remain” counts flights required before the end of the current month to stay or become eligible for the next season.</p>
      </section>
    </div>
  );
}
