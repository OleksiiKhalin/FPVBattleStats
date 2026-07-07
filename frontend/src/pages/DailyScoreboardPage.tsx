import { fetchJson } from "../api/client";
import type { ScoreboardResponse } from "../api/types";
import { ScoreboardTable } from "../components/ScoreboardTable";
import { useApi } from "../hooks/useApi";

type Props = {
  raceClass: string;
  selectedDate: string;
};

export function DailyScoreboardPage({ raceClass, selectedDate }: Props) {
  const { data, error, loading } = useApi<ScoreboardResponse>(
    () => fetchJson(`/scoreboards/${raceClass}/${selectedDate}`),
    [raceClass, selectedDate],
  );

  if (loading) {
    return <div className="panel">Loading scoreboard...</div>;
  }
  if (error || !data) {
    return <div className="panel">Scoreboard unavailable: {error ?? "No data"}</div>;
  }
  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">{raceClass} daily</p>
            <h2>Database-backed leaderboard</h2>
          </div>
          <div className="meta">
            <span>Source: local FPVBattle database</span>
            <span>Date: {selectedDate}</span>
          </div>
        </div>
      </section>
      <ScoreboardTable data={data} selectedDate={selectedDate} />
    </div>
  );
}
