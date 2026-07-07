import { useSearchParams, useParams } from "react-router-dom";

import { fetchJson } from "../api/client";
import type { CountryStatsRow, PilotAnalyticsResponse } from "../api/types";
import { StreakBoard } from "../components/StreakBoard";
import { TrendChart } from "../components/TrendChart";
import { usePilot } from "../context/PilotContext";
import { useApi } from "../hooks/useApi";

export function AnalyticsPage() {
  const { raceClass = "open" } = useParams();
  const { selectedPilot } = usePilot();
  const [searchParams] = useSearchParams();
  const pilot = searchParams.get("pilot") ?? selectedPilot;

  const analytics = useApi<PilotAnalyticsResponse>(
    () => fetchJson(`/analytics/pilots/${raceClass}/${encodeURIComponent(pilot)}`),
    [raceClass, pilot],
  );
  const countries = useApi<CountryStatsRow[]>(() => fetchJson(`/analytics/countries/${raceClass}`), [raceClass]);

  const countrySummary = countries.data ?? [];

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">{raceClass} analytics</p>
            <h2>{pilot}</h2>
          </div>
          <div className="meta">
            <span>The pilot in the header defines the analytics viewpoint across pages.</span>
          </div>
        </div>
      </section>

      {analytics.data ? <TrendChart data={analytics.data.points_timeline} /> : <div className="panel">Loading analytics...</div>}

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Countries</p>
            <h2>Season summary</h2>
          </div>
        </div>
        <table className="scoreboard">
          <thead>
            <tr>
              <th>Country</th>
              <th>Unique pilots</th>
              <th>Avg season score</th>
              <th>Avg place</th>
              <th>Wins</th>
              <th>Medals</th>
            </tr>
          </thead>
          <tbody>
            {countrySummary.map((row) => (
              <tr key={row.country ?? "unknown"}>
                <td>{row.country ?? "Unknown"}</td>
                <td>{row.unique_pilots}</td>
                <td>{row.avg_season_score ?? "-"}</td>
                <td>{row.avg_place ?? "-"}</td>
                <td>{row.season_wins}</td>
                <td>
                  {"🥇".repeat(row.gold_medals)}
                  {"🥈".repeat(row.silver_medals)}
                  {"🥉".repeat(row.bronze_medals)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {analytics.data ? <StreakBoard streaks={analytics.data.streaks} /> : null}
      {analytics.error ? <div className="panel">Pilot analytics unavailable: {analytics.error}</div> : null}
    </div>
  );
}
