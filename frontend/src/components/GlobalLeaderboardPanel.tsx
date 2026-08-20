import { useMemo, useState } from "react";

import type { GlobalLeaderboardResponse, GlobalLeaderboardRow } from "../api/types";

type Props = {
  data: GlobalLeaderboardResponse;
  selectedPilot: string;
};

type ForecastMode = "weekly" | "monthly";

function leagueLabel(league: string | null) {
  if (!league) return "Candidate";
  return league[0].toUpperCase() + league.slice(1);
}

function rankLabel(row: GlobalLeaderboardRow) {
  return row.rank ? `#${row.rank}` : "—";
}

function deltaLabel(row: GlobalLeaderboardRow) {
  if (row.rank_delta === null) return "—";
  if (row.rank_delta === 0) return "—";
  return row.rank_delta > 0 ? `↑ ${row.rank_delta}` : `↓ ${Math.abs(row.rank_delta)}`;
}

export function GlobalLeaderboardPanel({ data, selectedPilot }: Props) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [leagueFilter, setLeagueFilter] = useState("all");
  const [forecastMode, setForecastMode] = useState<ForecastMode>("weekly");
  const rows = useMemo(() => data.rows.filter((row) => (
    (statusFilter === "all" || row.status === statusFilter)
    && (leagueFilter === "all" || row.league === leagueFilter)
  )), [data.rows, leagueFilter, statusFilter]);
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
            <span>Official snapshot: {data.last_official_snapshot_date ?? "not created yet"}</span>
          </div>
        </div>
        {focus ? (
          <>
            <div className="stat-grid global-leaderboard-kpis">
              <div className="stat-card"><span>Current league / rank</span><strong>{leagueLabel(focus.league)} {rankLabel(focus)}</strong></div>
              <div className="stat-card"><span>Flight-days / 30</span><strong>{focus.flight_days} / {data.window_days}</strong></div>
              <div className="stat-card"><span>Days without flight</span><strong>{focus.inactive_days}</strong></div>
              <div className="stat-card"><span>Adjusted average gap</span><strong>{focus.adjusted_average_gap === null ? "—" : `${focus.adjusted_average_gap}s`}</strong></div>
              <div className="stat-card"><span>Status</span><strong className={`status-${focus.status}`}>{focus.status.replace("_", " ")}</strong></div>
              <div className="stat-card"><span>Next league</span><strong>{focus.target_league ? `${leagueLabel(focus.target_league)} / ${focus.gap_to_next_league ?? "—"}s` : "Top league"}</strong></div>
            </div>
            <p className="chart-note">{focus.status_reason}</p>
            {forecast ? (
              <div className="forecast-strip">
                <div className="toggle-row">
                  <button type="button" className={forecastMode === "weekly" ? "chip active" : "chip"} onClick={() => setForecastMode("weekly")}>Next Monday</button>
                  <button type="button" className={forecastMode === "monthly" ? "chip active" : "chip"} onClick={() => setForecastMode("monthly")}>Next month</button>
                </div>
                <span>Without flying: {forecast.no_flight_days} days</span>
                <span>If flying daily: {forecast.continue_flight_days} days</span>
                <span>Projected league: {leagueLabel(forecast.continue_league)}</span>
              </div>
            ) : null}
          </>
        ) : <p>No active results in the current 30-day window.</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Current field</p>
            <h2>Active pilots and league risk</h2>
          </div>
          <div className="toggle-row leaderboard-filters">
            <label>Status <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All</option><option value="qualified">Qualified</option><option value="at_risk">At risk</option><option value="candidate">Candidate</option><option value="guaranteed_out">Guaranteed out</option></select></label>
            <label>League <select value={leagueFilter} onChange={(event) => setLeagueFilter(event.target.value)}><option value="all">All</option><option value="gold">Gold</option><option value="silver">Silver</option><option value="bronze">Bronze</option></select></label>
          </div>
        </div>
        <div className="table-scroll">
          <table className="scoreboard compact-scoreboard global-leaderboard-table">
            <thead><tr><th>Rank</th><th>Pilot</th><th>League</th><th>Days</th><th>Inactive</th><th>Avg gap</th><th>Change</th><th>Outlook</th></tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row.pilot} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                <td>{rankLabel(row)}</td>
                <td><strong>{row.pilot}</strong>{row.country ? <small className="table-muted"> {row.country}</small> : null}</td>
                <td><span className={`league-pill league-${row.league ?? "candidate"}`}>{leagueLabel(row.league)}</span></td>
                <td>{row.flight_days}/{data.window_days}</td>
                <td>{row.inactive_days}</td>
                <td>{row.adjusted_average_gap === null ? "—" : `${row.adjusted_average_gap}s`}</td>
                <td>{deltaLabel(row)}</td>
                <td><span className={`status-pill status-${row.status}`}>{row.status.replace("_", " ")}</span><small className="table-reason">{row.status_reason}</small></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="chart-note">The leaderboard uses the average gap to the daily top-three average, excluding one worst day. Statuses are explainable activity scenarios, not statistically calibrated probabilities.</p>
      </section>
    </div>
  );
}
