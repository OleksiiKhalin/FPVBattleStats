import { useEffect, useMemo, useState } from "react";

import { fetchJson } from "../api/client";
import type { PilotComparisonDay, PilotComparisonResponse, PilotOption } from "../api/types";
import { useApi } from "../hooks/useApi";

type Props = {
  primaryPilot: string;
  raceClass: string;
  dateFrom: string;
  dateTo: string;
};

function buildComparisonPath(raceClass: string, primaryPilot: string, opponentPilot: string, dateFrom: string, dateTo: string, season: string) {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (season) params.set("season", season);
  return `/analytics/pilot-compare/${raceClass}/${encodeURIComponent(primaryPilot)}/${encodeURIComponent(opponentPilot)}?${params.toString()}`;
}

function formatNumber(value: number | null, suffix = "") {
  return value === null ? "-" : `${value}${suffix}`;
}

function monthLabel(value: string) {
  return new Date(`${value}-01T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function comparisonTileStyle(day: PilotComparisonDay): React.CSSProperties {
  if (day.difference_percent === null) return {};
  const intensity = Math.min(0.78, 0.25 + Math.abs(day.difference_percent) / 16);
  return { backgroundColor: day.difference_percent > 0 ? `rgba(39, 170, 104, ${intensity})` : `rgba(198, 66, 66, ${intensity})` };
}

function PilotSummary({ name, stats }: { name: string; stats: PilotComparisonResponse["primary"] }) {
  return (
    <section className="comparison-pilot-summary">
      <h3>{name}</h3>
      <div className="comparison-stat-list">
        <span>Days flown <strong>{stats.flights}</strong></span>
        <span>Longest streak <strong>{stats.longest_streak} days</strong></span>
        <span>Average gap to leader <strong>{formatNumber(stats.average_gap_to_leader, " s")}</strong></span>
        <span>Total score <strong>{stats.total_score}</strong></span>
      </div>
      <div className="league-places">
        {Object.entries(stats.average_place_by_category).map(([league, averagePlace]) => (
          <span key={league}>{league}: <strong>{formatNumber(averagePlace)}</strong></span>
        ))}
      </div>
    </section>
  );
}

export function PilotComparisonPanel({ primaryPilot, raceClass, dateFrom, dateTo }: Props) {
  const [opponentPilot, setOpponentPilot] = useState("");
  const [season, setSeason] = useState("");
  const pilots = useApi<PilotOption[]>(() => fetchJson(`/analytics/pilots?race_class=${raceClass}`), [raceClass]);

  useEffect(() => {
    const nextOpponent = pilots.data?.find((pilot) => pilot.pilot !== primaryPilot)?.pilot ?? "";
    setOpponentPilot(nextOpponent);
  }, [pilots.data, primaryPilot, raceClass]);

  const comparison = useApi<PilotComparisonResponse>(
    () => fetchJson(buildComparisonPath(raceClass, primaryPilot, opponentPilot, dateFrom, dateTo, season)),
    [raceClass, primaryPilot, opponentPilot, dateFrom, dateTo, season],
  );

  const months = useMemo(() => {
    const grouped = new Map<string, PilotComparisonDay[]>();
    for (const day of comparison.data?.days ?? []) {
      const month = day.date.slice(0, 7);
      grouped.set(month, [...(grouped.get(month) ?? []), day]);
    }
    return [...grouped.entries()];
  }, [comparison.data]);

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Head-to-head</p>
            <h2>Compare {primaryPilot} against another pilot</h2>
          </div>
          <div className="meta"><span>Overall uses the selected class and date range. A season narrows that same range.</span></div>
        </div>
        <div className="filters-grid comparison-filters">
          <label className="field">
            <span>Compare with</span>
            <select value={opponentPilot} onChange={(event) => setOpponentPilot(event.target.value)}>
              {pilots.data?.filter((pilot) => pilot.pilot !== primaryPilot).map((pilot) => <option key={pilot.pilot} value={pilot.pilot}>{pilot.pilot}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Statistics scope</span>
            <select value={season} onChange={(event) => setSeason(event.target.value)}>
              <option value="">Overall</option>
              {comparison.data?.seasons.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
        </div>
      </section>

      {comparison.loading ? <div className="panel">Loading comparison...</div> : null}
      {comparison.error ? <div className="panel">Comparison unavailable: {comparison.error}</div> : null}
      {comparison.data ? <>
        <section className="panel">
          <div className="panel-header"><div><p className="eyebrow">Shared race days</p><h2>Matchup KPIs</h2></div></div>
          <div className="stat-grid comparison-kpis">
            <div className="stat-card"><span>{primaryPilot} win rate</span><strong>{formatNumber(comparison.data.win_rate, "%")}</strong></div>
            <div className="stat-card"><span>Wins / shared days</span><strong>{comparison.data.primary_wins} / {comparison.data.shared_days}</strong></div>
            <div className="stat-card"><span>Gap-to-leader difference</span><strong>{formatNumber(comparison.data.primary.average_gap_to_leader === null || comparison.data.opponent.average_gap_to_leader === null ? null : Number((comparison.data.primary.average_gap_to_leader - comparison.data.opponent.average_gap_to_leader).toFixed(3)), " s")}</strong></div>
          </div>
        </section>

        <section className="panel comparison-pilots">
          <PilotSummary name={primaryPilot} stats={comparison.data.primary} />
          <PilotSummary name={opponentPilot} stats={comparison.data.opponent} />
        </section>

        <section className="panel">
          <div className="panel-header"><div><p className="eyebrow">Daily results</p><h2>Monthly head-to-head calendar</h2></div></div>
          <div className="comparison-calendar-list">
            {months.map(([month, days]) => {
              const leadingBlanks = new Date(`${month}-01T00:00:00`).getDay();
              return <section className="comparison-month" key={month}>
                <h3>{monthLabel(month)}</h3>
                <div className="comparison-weekdays">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((label) => <span key={label}>{label}</span>)}</div>
                <div className="comparison-calendar">
                  {Array.from({ length: leadingBlanks }, (_, index) => <span className="comparison-day blank" key={`blank-${index}`} />)}
                  {days.map((day) => <div className={day.difference_seconds === null ? "comparison-day missing" : "comparison-day"} style={comparisonTileStyle(day)} key={day.date} title={`${day.date}: ${day.difference_seconds === null ? "one or both pilots did not fly" : `${day.difference_seconds > 0 ? "+" : ""}${day.difference_seconds} seconds for ${primaryPilot}`}`}>
                    <small>{day.date.slice(8)}</small>
                    <strong>{day.difference_seconds === null ? "-" : `${day.difference_seconds > 0 ? "+" : ""}${day.difference_seconds}s`}</strong>
                  </div>)}
                </div>
              </section>;
            })}
          </div>
          <p className="chart-note">Each square shows the seconds difference: positive green means {primaryPilot} was faster, while negative red means they were slower. Stronger colour means a larger percentage difference. Black squares show days when at least one pilot did not fly.</p>
        </section>
      </> : null}
    </div>
  );
}
