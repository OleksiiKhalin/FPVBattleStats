import { fetchJson } from "../api/client";
import type { ScoreboardResponse } from "../api/types";
import { ScoreboardTable } from "../components/ScoreboardTable";
import { useApi } from "../hooks/useApi";

type Props = {
  raceClass: string;
};

const TODAY = new Date().toISOString().slice(0, 10);

export function DailyScoreboardPage({ raceClass }: Props) {
  const { data, error, loading } = useApi<ScoreboardResponse>(
    () => fetchJson(`/scoreboards/${raceClass}/${TODAY}`),
    [raceClass],
  );

  if (loading) {
    return <div className="panel">Loading scoreboard...</div>;
  }
  if (error || !data) {
    return <div className="panel">Scoreboard unavailable: {error ?? "No data"}</div>;
  }
  return <ScoreboardTable data={data} />;
}
