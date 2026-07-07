import { Bar, BarChart, Brush, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useMemo, useState } from "react";

import { fetchJson } from "../api/client";
import type {
  ConsistencyRow,
  CountryStatsRow,
  GeneralStatsResponse,
  QuadStatsRow,
  SeasonStatsRow,
  TrackRatingRow,
} from "../api/types";
import { RangeQuickFilters } from "../components/RangeQuickFilters";
import { usePilot } from "../context/PilotContext";
import { useApi } from "../hooks/useApi";

type GeneralSection = "countries" | "quads" | "tracks" | "seasons" | "participation" | "consistency";
type SortDirection = "asc" | "desc";
type CountrySortKey = keyof Pick<CountryStatsRow, "country" | "unique_pilots" | "avg_season_score" | "avg_place" | "season_wins" | "medals_per_pilot">;
type QuadSortKey = keyof Pick<QuadStatsRow, "quad" | "category" | "entries" | "usage_percentage" | "unique_pilots" | "avg_place" | "wins">;
type TrackSortKey = keyof Pick<TrackRatingRow, "track" | "votes" | "average_score" | "weighted_score">;
type SeasonSortKey = keyof Pick<SeasonStatsRow, "season" | "unique_pilots" | "consistent_pilots" | "largest_victory_margin">;
type ConsistencySortKey = keyof Pick<ConsistencyRow, "pilot" | "country" | "appearances" | "dispersion" | "average_place" | "consistency_score" | "first_flight_date" | "last_flight_date">;
type ImprovementSortKey = keyof Pick<ConsistencyRow, "pilot" | "country" | "appearances" | "improvement_score">;

const DEFAULT_FROM = "2023-11-15";
const DEFAULT_TO = new Date().toISOString().slice(0, 10);

function buildGeneralStatsPath(raceClass: string, dateFrom: string, dateTo: string, pilotName: string) {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    pilot_name: pilotName,
  });
  return `/analytics/general-stats/${raceClass}?${params.toString()}`;
}

function sortRows<T extends Record<string, string | number | null>>(rows: T[], key: keyof T, direction: SortDirection) {
  return [...rows].sort((left, right) => {
    const leftValue = left[key];
    const rightValue = right[key];
    if (leftValue === rightValue) {
      return 0;
    }
    if (leftValue === null) {
      return 1;
    }
    if (rightValue === null) {
      return -1;
    }
    if (direction === "asc") {
      return leftValue > rightValue ? 1 : -1;
    }
    return leftValue < rightValue ? 1 : -1;
  });
}

function toggleSort<T extends string>(
  current: { key: T; direction: SortDirection },
  setState: (state: { key: T; direction: SortDirection }) => void,
  nextKey: T,
) {
  if (current.key === nextKey) {
    setState({ key: nextKey, direction: current.direction === "asc" ? "desc" : "asc" });
    return;
  }
  setState({ key: nextKey, direction: nextKey === "country" || nextKey === "pilot" || nextKey === "track" || nextKey === "season" ? "asc" : "desc" });
}

export function GeneralStatsPage() {
  const { selectedPilot } = usePilot();
  const [raceClass, setRaceClass] = useState("open");
  const [dateFrom, setDateFrom] = useState(DEFAULT_FROM);
  const [dateTo, setDateTo] = useState(DEFAULT_TO);
  const [section, setSection] = useState<GeneralSection>("countries");
  const [countrySort, setCountrySort] = useState<{ key: CountrySortKey; direction: SortDirection }>({ key: "unique_pilots", direction: "desc" });
  const [quadSort, setQuadSort] = useState<{ key: QuadSortKey; direction: SortDirection }>({ key: "entries", direction: "desc" });
  const [trackSort, setTrackSort] = useState<{ key: TrackSortKey; direction: SortDirection }>({ key: "weighted_score", direction: "desc" });
  const [seasonSort, setSeasonSort] = useState<{ key: SeasonSortKey; direction: SortDirection }>({ key: "season", direction: "desc" });
  const [consistencySort, setConsistencySort] = useState<{ key: ConsistencySortKey; direction: SortDirection }>({ key: "consistency_score", direction: "desc" });
  const [improvementSort, setImprovementSort] = useState<{ key: ImprovementSortKey; direction: SortDirection }>({ key: "improvement_score", direction: "desc" });

  const stats = useApi<GeneralStatsResponse>(
    () => fetchJson(buildGeneralStatsPath(raceClass, dateFrom, dateTo, selectedPilot)),
    [raceClass, dateFrom, dateTo, selectedPilot],
  );

  const sectionLabel = {
    countries: "Country Stats",
    quads: "Quad Stats",
    tracks: "Track Rating",
    seasons: "Season Stats",
    participation: "Participation",
    consistency: "Consistency",
  };

  const countryRows = useMemo(() => (stats.data ? sortRows(stats.data.countries, countrySort.key, countrySort.direction) : []), [stats.data, countrySort]);
  const quadRows = useMemo(() => (stats.data ? sortRows(stats.data.quads, quadSort.key, quadSort.direction) : []), [stats.data, quadSort]);
  const trackRows = useMemo(() => (stats.data ? sortRows(stats.data.track_ratings, trackSort.key, trackSort.direction) : []), [stats.data, trackSort]);
  const seasonRows = useMemo(() => (stats.data ? sortRows(stats.data.seasons, seasonSort.key, seasonSort.direction) : []), [stats.data, seasonSort]);
  const consistencyRows = useMemo(() => (stats.data ? sortRows(stats.data.consistency_leaderboard, consistencySort.key, consistencySort.direction) : []), [stats.data, consistencySort]);
  const improvementRows = useMemo(() => (stats.data ? sortRows(stats.data.best_improvement, improvementSort.key, improvementSort.direction) : []), [stats.data, improvementSort]);

  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">General stats</p>
            <h2>{raceClass} class showcase analytics</h2>
          </div>
          <div className="meta">
            <span>Selected pilot consistency highlight: {selectedPilot}</span>
            <span>Date period affects stats except the consistency section, which is all-time.</span>
          </div>
        </div>

        <div className="filters-grid">
          <label className="field">
            <span>Class</span>
            <select value={raceClass} onChange={(event) => setRaceClass(event.target.value)}>
              <option value="open">Open</option>
              <option value="whoop">Whoop</option>
            </select>
          </label>
          <label className="field">
            <span>From</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label className="field">
            <span>To</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
        </div>

        <RangeQuickFilters onApply={(from, to) => { setDateFrom(from); setDateTo(to); }} />

        <div className="section-tabs">
          {Object.entries(sectionLabel).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={section === value ? "chip active" : "chip"}
              onClick={() => setSection(value as GeneralSection)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {stats.loading ? <div className="panel">Loading general stats...</div> : null}
      {stats.error ? <div className="panel">General stats unavailable: {stats.error}</div> : null}

      {stats.data && section === "countries" ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Country statistics</p>
              <h2>Season-weighted medal and placement summary</h2>
            </div>
          </div>
          <table className="scoreboard">
            <thead><tr>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "country")}>Country</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "unique_pilots")}>Unique pilots</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "avg_season_score")}>Avg season score</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "avg_place")}>Avg place</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "season_wins")}>Season wins</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(countrySort, setCountrySort, "medals_per_pilot")}>Medals per pilot</button></th>
              <th>Medals</th>
            </tr></thead>
            <tbody>{countryRows.map((row) => (
              <tr key={row.country ?? "unknown"}>
                <td>{row.country ?? "Unknown"}</td><td>{row.unique_pilots}</td><td>{row.avg_season_score ?? "-"}</td><td>{row.avg_place ?? "-"}</td><td>{row.season_wins}</td><td>{row.medals_per_pilot ?? "-"}</td><td>{"🥇".repeat(row.gold_medals)}{"🥈".repeat(row.silver_medals)}{"🥉".repeat(row.bronze_medals)}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      ) : null}

      {stats.data && section === "quads" ? (
        <section className="panel">
          <div className="panel-header"><div><p className="eyebrow">Quad statistics</p><h2>Usage, category mix, and wins</h2></div></div>
          <table className="scoreboard">
            <thead><tr>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "quad")}>Quad</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "category")}>Category</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "entries")}>Entries</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "usage_percentage")}>Usage %</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "unique_pilots")}>Unique pilots</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "avg_place")}>Avg place</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(quadSort, setQuadSort, "wins")}>Wins</button></th>
            </tr></thead>
            <tbody>{quadRows.map((row) => (
              <tr key={`${row.quad}-${row.category ?? "overall"}`}>
                <td>{row.quad}</td><td>{row.category ?? "Overall"}</td><td>{row.entries}</td><td>{row.usage_percentage}</td><td>{row.unique_pilots}</td><td>{row.avg_place ?? "-"}</td><td>{row.wins}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      ) : null}

      {stats.data && section === "tracks" ? (
        <section className="panel">
          <div className="panel-header"><div><p className="eyebrow">Track rating</p><h2>Mock showcase leaderboard</h2></div></div>
          <table className="scoreboard">
            <thead><tr>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(trackSort, setTrackSort, "track")}>Track</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(trackSort, setTrackSort, "votes")}>Votes</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(trackSort, setTrackSort, "average_score")}>Average score</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(trackSort, setTrackSort, "weighted_score")}>Weighted score</button></th>
            </tr></thead>
            <tbody>{trackRows.map((row) => (
              <tr key={row.track}><td>{row.track}</td><td>{row.votes}</td><td>{row.average_score}</td><td>{row.weighted_score}</td></tr>
            ))}</tbody>
          </table>
        </section>
      ) : null}

      {stats.data && section === "seasons" ? (
        <section className="panel">
          <div className="panel-header"><div><p className="eyebrow">Season stats</p><h2>Newest-first season summary</h2></div></div>
          <table className="scoreboard">
            <thead><tr>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(seasonSort, setSeasonSort, "season")}>Season</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(seasonSort, setSeasonSort, "unique_pilots")}>Unique pilots</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(seasonSort, setSeasonSort, "consistent_pilots")}>Consistent pilots</button></th>
              <th><button type="button" className="sort-button" onClick={() => toggleSort(seasonSort, setSeasonSort, "largest_victory_margin")}>Largest victory margin</button></th>
            </tr></thead>
            <tbody>{seasonRows.map((row) => (
              <tr key={row.season}><td>{row.season}</td><td>{row.unique_pilots}</td><td>{row.consistent_pilots}</td><td>{row.largest_victory_margin ?? "-"}{row.largest_victory_margin !== null ? " s" : ""}</td></tr>
            ))}</tbody>
          </table>
          <p className="chart-note">A consistent pilot is counted here when they appear on at least half of the season’s tracked days. Largest victory margin is the gap between first and second place in seconds.</p>
        </section>
      ) : null}

      {stats.data && section === "participation" ? (
        <section className="panel chart-panel">
          <div className="panel-header">
            <div><p className="eyebrow">Participation statistics</p><h2>Daily count, average, peaks, and trend</h2></div>
            <div className="meta">
              <span>Average: {stats.data.participation.average_participants}</span>
              <span>Peak: {stats.data.participation.peak_participation_day?.date ?? "-"} ({stats.data.participation.peak_participation_day?.participants ?? 0})</span>
              <span>Low: {stats.data.participation.lowest_participation_day?.date ?? "-"} ({stats.data.participation.lowest_participation_day?.participants ?? 0})</span>
              <span>Trend: {stats.data.participation.participation_trend ?? "-"}</span>
            </div>
          </div>
          <div className="chart-actions"><span className="chart-hint">Use the brush below to zoom and inspect a sector.</span></div>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={stats.data.participation.daily_counts}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="date" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="participants" fill="#7ef3c5" radius={[4, 4, 0, 0]} />
              <Brush dataKey="date" height={24} stroke="#7ef3c5" travellerWidth={10} />
            </BarChart>
          </ResponsiveContainer>
          <p className="chart-note">Participation trend is the simple difference between the first and last visible daily participant counts in the selected range.</p>
        </section>
      ) : null}

      {stats.data && section === "consistency" ? (
        <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <div><p className="eyebrow">Selected pilot</p><h2>{selectedPilot} all-time consistency snapshot</h2></div>
              <div className="meta"><span>This section ignores the date filters.</span><span>Score uses only dispersion and appearance count.</span></div>
            </div>
            {stats.data.selected_pilot_consistency ? (
              <div className="stat-grid">
                <div className="stat-card"><span>Score</span><strong>{stats.data.selected_pilot_consistency.consistency_score}</strong></div>
                <div className="stat-card"><span>Dispersion</span><strong>{stats.data.selected_pilot_consistency.dispersion}</strong></div>
                <div className="stat-card"><span>Appearances</span><strong>{stats.data.selected_pilot_consistency.appearances}</strong></div>
                <div className="stat-card"><span>Avg place</span><strong>{stats.data.selected_pilot_consistency.average_place ?? "-"}</strong></div>
                <div className="stat-card"><span>First flight</span><strong>{stats.data.selected_pilot_consistency.first_flight_date}</strong></div>
                <div className="stat-card"><span>Last flight</span><strong>{stats.data.selected_pilot_consistency.last_flight_date}</strong></div>
              </div>
            ) : <p>No all-time consistency data for the selected pilot in this class.</p>}
            <p className="chart-note">Dispersion is the mean absolute deviation of finishing places around the pilot’s own average place. Consistency score multiplies low dispersion by a logarithmic appearance weight.</p>
          </section>

          <section className="panel">
            <div className="panel-header"><div><p className="eyebrow">Consistency leaderboard</p><h2>All-time class ranking by dispersion and appearances</h2></div></div>
            <table className="scoreboard">
              <thead><tr>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "pilot")}>Pilot</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "country")}>Country</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "appearances")}>Appearances</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "dispersion")}>Dispersion</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "average_place")}>Avg place</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "first_flight_date")}>First flight</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "last_flight_date")}>Last flight</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(consistencySort, setConsistencySort, "consistency_score")}>Consistency score</button></th>
              </tr></thead>
              <tbody>{consistencyRows.map((row) => (
                <tr key={row.pilot} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                  <td>{row.pilot}</td><td>{row.country ?? "-"}</td><td>{row.appearances}</td><td>{row.dispersion}</td><td>{row.average_place ?? "-"}</td><td>{row.first_flight_date}</td><td>{row.last_flight_date}</td><td>{row.consistency_score}</td>
                </tr>
              ))}</tbody>
            </table>
            <p className="chart-note">This leaderboard ignores the date filters and uses every stored result in the selected class.</p>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div><p className="eyebrow">Best improvement</p><h2>All-time improvement trend by class</h2></div>
              <div className="meta"><span>Uses the full appearance history.</span><span>Higher score means place trends downward over time.</span></div>
            </div>
            <table className="scoreboard">
              <thead><tr>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(improvementSort, setImprovementSort, "pilot")}>Pilot</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(improvementSort, setImprovementSort, "country")}>Country</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(improvementSort, setImprovementSort, "appearances")}>Appearances</button></th>
                <th><button type="button" className="sort-button" onClick={() => toggleSort(improvementSort, setImprovementSort, "improvement_score")}>Improvement score</button></th>
              </tr></thead>
              <tbody>{improvementRows.map((row) => (
                <tr key={`improvement-${row.pilot}`} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                  <td>{row.pilot}</td><td>{row.country ?? "-"}</td><td>{row.appearances}</td><td>{row.improvement_score ?? "-"}</td>
                </tr>
              ))}</tbody>
            </table>
            <p className="chart-note">Improvement score is the negative slope of the pilot’s finishing places over appearance order. Positive values mean the pilot tends to finish better over time.</p>
          </section>
        </div>
      ) : null}
    </div>
  );
}
