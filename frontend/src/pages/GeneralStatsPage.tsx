import { Bar, BarChart, Brush, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { fetchJson } from "../api/client";
import type {
  ConsistencyRow,
  CountryStatsRow,
  GeneralStatsResponse,
  ProgressCorrelationResponse,
  QuadStatsRow,
  SeasonStatsRow,
  TrackRatingRow,
} from "../api/types";
import { RangeQuickFilters } from "../components/RangeQuickFilters";
import { usePilot } from "../context/PilotContext";
import { useApi } from "../hooks/useApi";

type GeneralSection = "countries" | "quads" | "tracks" | "seasons" | "participation" | "easy-days" | "consistency" | "day-streaks" | "progress-correlation";
type DayStreakView = "streaks" | "days-flown";
type StreakMode = "best" | "best-active" | "all";
type StreakFilter = "all" | "active" | "inactive";
type SortDirection = "asc" | "desc";
type CountrySortKey = keyof Pick<CountryStatsRow, "country" | "unique_pilots" | "avg_season_score" | "avg_place" | "season_wins" | "medals_per_pilot">;
type QuadSortKey = keyof Pick<QuadStatsRow, "quad" | "category" | "entries" | "usage_percentage" | "unique_pilots" | "avg_place" | "wins">;
type TrackSortKey = keyof Pick<TrackRatingRow, "track" | "votes" | "average_score" | "weighted_score">;
type SeasonSortKey = keyof Pick<SeasonStatsRow, "season" | "unique_pilots" | "consistent_pilots" | "largest_victory_margin">;
type ConsistencySortKey = keyof Pick<ConsistencyRow, "pilot" | "country" | "appearances" | "dispersion" | "average_place" | "consistency_score" | "first_flight_date" | "last_flight_date">;
type ImprovementSortKey = keyof Pick<ConsistencyRow, "pilot" | "country" | "appearances" | "improvement_score">;

const DEFAULT_FROM = "2023-11-15";
const DEFAULT_TO = new Date().toISOString().slice(0, 10);
const DEFAULT_CORRELATION_FROM = "2026-03-01";

function CorrelationTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: Record<string, unknown> }> }) {
  if (!active || !payload?.length || !payload[0].payload) {
    return null;
  }
  const point = payload[0].payload;
  const pilot = typeof point.pilot === "string" ? point.pilot : "Population average";
  const date = typeof point.date === "string" ? point.date : null;
  const daysFlown = typeof point.days_flown === "number" ? point.days_flown : null;
  const gap = typeof point.gap_percentage === "number" ? point.gap_percentage : point.average_gap_percentage;
  const sampleSize = typeof point.sample_size === "number" ? point.sample_size : null;
  return (
    <div className="correlation-tooltip">
      <strong>{pilot}</strong>
      {date ? <span>Date: {date}</span> : null}
      {daysFlown !== null ? <span>Days flown: {daysFlown}</span> : null}
      {typeof gap === "number" ? <span>Gap: {gap.toFixed(3)}%</span> : null}
      {sampleSize !== null ? <span>Sample: {sampleSize}</span> : null}
    </div>
  );
}

function buildGeneralStatsPath(raceClass: string, dateFrom: string, dateTo: string, pilotName: string, consistentPilotsOnly: boolean) {
  const params = new URLSearchParams({ pilot_name: pilotName });
  if (dateFrom) {
    params.set("date_from", dateFrom);
  }
  if (dateTo) {
    params.set("date_to", dateTo);
  }
  if (consistentPilotsOnly) {
    params.set("consistent_pilots_only", "true");
  }
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

function readStreakMode(value: string | null): StreakMode {
  return value === "best-active" || value === "all" ? value : "best";
}

function readStreakFilter(value: string | null): StreakFilter {
  return value === "active" || value === "inactive" ? value : "all";
}

export function GeneralStatsPage() {
  const { selectedPilot } = usePilot();
  const [searchParams, setSearchParams] = useSearchParams();
  const [raceClass, setRaceClass] = useState(searchParams.get("class") ?? "open");
  const [dateFrom, setDateFrom] = useState(searchParams.get("from") ?? DEFAULT_FROM);
  const [dateTo, setDateTo] = useState(searchParams.get("to") ?? DEFAULT_TO);
  const [section, setSection] = useState<GeneralSection>((searchParams.get("section") as GeneralSection | null) ?? "countries");
  const [correlationFrom, setCorrelationFrom] = useState(searchParams.get("correlation_from") ?? DEFAULT_CORRELATION_FROM);
  const [showCorrelationPoints, setShowCorrelationPoints] = useState(true);
  const [showCorrelationAverage, setShowCorrelationAverage] = useState(true);
  const [showCorrelationViewport, setShowCorrelationViewport] = useState(true);
  const [dayStreakView, setDayStreakView] = useState<DayStreakView>(searchParams.get("streak_view") === "days-flown" ? "days-flown" : "streaks");
  const [streakMode, setStreakMode] = useState<StreakMode>(readStreakMode(searchParams.get("streak_mode")));
  const [streakFilter, setStreakFilter] = useState<StreakFilter>(readStreakFilter(searchParams.get("streak_filter")));
  const [consistentPilotsOnly, setConsistentPilotsOnly] = useState(searchParams.get("consistent") === "true");
  const [seasonScope, setSeasonScope] = useState("");
  const [countrySort, setCountrySort] = useState<{ key: CountrySortKey; direction: SortDirection }>({ key: "unique_pilots", direction: "desc" });
  const [quadSort, setQuadSort] = useState<{ key: QuadSortKey; direction: SortDirection }>({ key: "entries", direction: "desc" });
  const [trackSort, setTrackSort] = useState<{ key: TrackSortKey; direction: SortDirection }>({ key: "weighted_score", direction: "desc" });
  const [seasonSort, setSeasonSort] = useState<{ key: SeasonSortKey; direction: SortDirection }>({ key: "season", direction: "desc" });
  const [consistencySort, setConsistencySort] = useState<{ key: ConsistencySortKey; direction: SortDirection }>({ key: "consistency_score", direction: "desc" });
  const [improvementSort, setImprovementSort] = useState<{ key: ImprovementSortKey; direction: SortDirection }>({ key: "improvement_score", direction: "desc" });
  const pilotFromQuery = searchParams.get("pilot");

  useEffect(() => {
    // PilotSelector owns URL -> context reconciliation. Do not write the
    // context default over a pilot from a deep link during the first render.
    if (pilotFromQuery && pilotFromQuery !== selectedPilot) {
      return;
    }
    const params = new URLSearchParams({ class: raceClass, pilot: selectedPilot, section });
    if (dateFrom) params.set("from", dateFrom);
    if (dateTo) params.set("to", dateTo);
    if (consistentPilotsOnly) params.set("consistent", "true");
    if (correlationFrom) params.set("correlation_from", correlationFrom);
    if (section === "day-streaks") {
      if (dayStreakView !== "streaks") params.set("streak_view", dayStreakView);
      if (streakMode !== "best") params.set("streak_mode", streakMode);
      if (streakFilter !== "all") params.set("streak_filter", streakFilter);
    }
    if (params.toString() !== searchParams.toString()) setSearchParams(params, { replace: true });
  }, [consistentPilotsOnly, correlationFrom, dateFrom, dateTo, dayStreakView, pilotFromQuery, raceClass, searchParams, section, selectedPilot, setSearchParams, streakFilter, streakMode]);
  const stats = useApi<GeneralStatsResponse>(
    () => fetchJson(buildGeneralStatsPath(raceClass, dateFrom, dateTo, selectedPilot, consistentPilotsOnly)),
    [raceClass, dateFrom, dateTo, selectedPilot, consistentPilotsOnly],
  );
  const correlation = useApi<ProgressCorrelationResponse>(
    () => fetchJson(`/analytics/progress-correlation/${raceClass}?${new URLSearchParams({ gap_from: correlationFrom, pilot_name: selectedPilot }).toString()}`),
    [correlationFrom, raceClass, selectedPilot],
  );

  const sectionLabel = {
    countries: "Country Stats",
    quads: "Quad Stats",
    tracks: "Track Rating",
    seasons: "Season Stats",
    participation: "Participation",
    "easy-days": "Easy Days",
    consistency: "Consistency",
    "day-streaks": "Day Streaks",
    "progress-correlation": "Progress Correlation",
  };

  const countryRows = useMemo(() => (stats.data ? sortRows(stats.data.countries, countrySort.key, countrySort.direction) : []), [stats.data, countrySort]);
  const quadRows = useMemo(() => (stats.data ? sortRows(stats.data.quads, quadSort.key, quadSort.direction) : []), [stats.data, quadSort]);
  const trackRows = useMemo(() => (stats.data ? sortRows(stats.data.track_ratings, trackSort.key, trackSort.direction) : []), [stats.data, trackSort]);
  const seasonRows = useMemo(() => (stats.data ? sortRows(stats.data.seasons, seasonSort.key, seasonSort.direction) : []), [stats.data, seasonSort]);
  const consistencyRows = useMemo(() => (stats.data ? sortRows(stats.data.consistency_leaderboard, consistencySort.key, consistencySort.direction) : []), [stats.data, consistencySort]);
  const improvementRows = useMemo(() => (stats.data ? sortRows(stats.data.best_improvement, improvementSort.key, improvementSort.direction) : []), [stats.data, improvementSort]);
  const visibleStreakRows = useMemo(() => {
    const allRows = stats.data?.day_streaks.streaks ?? [];
    const modeRows = streakMode === "best" ? allRows.filter((row) => row.is_best) : streakMode === "best-active" ? allRows.filter((row) => row.is_best || row.is_active) : allRows;
    if (streakFilter === "active") return modeRows.filter((row) => row.is_active);
    if (streakFilter === "inactive") return modeRows.filter((row) => !row.is_active);
    return modeRows;
  }, [stats.data, streakFilter, streakMode]);
  const dayStreakStats = stats.data?.day_streaks;
  const correlationData = correlation.data;
  const viewportCorrelationPoints = useMemo(
    () => correlationData?.points.filter((point) => point.pilot === selectedPilot) ?? [],
    [correlationData, selectedPilot],
  );

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
            <span>Date period affects stats except Consistency and Progress Correlation, which use their own all-time history rules.</span>
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

        <RangeQuickFilters
          onApply={(from, to) => { setDateFrom(from); setDateTo(to); setSeasonScope(""); }}
          onClear={() => { setDateFrom(""); setDateTo(""); setSeasonScope(""); }}
          seasons={stats.data?.seasons.map((row) => row.season) ?? []}
          season={seasonScope}
          onSeasonChange={(value) => {
            setSeasonScope(value);
            if (!value) { setDateFrom(""); setDateTo(""); return; }
            const [year, month] = value.split("-").map(Number);
            setDateFrom(`${value}-01`);
            setDateTo(new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10));
          }}
        />

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
      {section === "progress-correlation" && correlation.loading ? <div className="panel">Loading progress correlation...</div> : null}
      {section === "progress-correlation" && correlation.error ? <div className="panel">Progress correlation unavailable: {correlation.error}</div> : null}

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


      {stats.data && section === "easy-days" ? (() => {
        const easyDays = stats.data.easy_days;
        const months = easyDays.daily_gaps.reduce<Record<string, typeof easyDays.daily_gaps>>((groups, day) => {
          const month = day.date.slice(0, 7);
          (groups[month] ??= []).push(day);
          return groups;
        }, {});
        const selected = easyDays.selected_day;
        const decision = selected?.is_favorable === true ? "Favorable: fly" : selected?.is_favorable === false ? "Tough day: consider skipping" : "No completed results";
        const generalReturnPath = `/general-stats?${new URLSearchParams({ class: raceClass, pilot: selectedPilot, section, ...(dateFrom ? { from: dateFrom } : {}), ...(dateTo ? { to: dateTo } : {}), ...(consistentPilotsOnly ? { consistent: "true" } : {}) }).toString()}`;
        return <div className="stack">
          <section className="panel">
            <div className="panel-header">
              <div><p className="eyebrow">Easy Days</p><h2>When the field stays closer to the leader</h2></div>
              <label className="toggle-row"><input type="checkbox" checked={consistentPilotsOnly} onChange={(event) => setConsistentPilotsOnly(event.target.checked)} /> Regular pilots only</label>
            </div>
            <div className="stat-grid">
              <div className="stat-card"><span>Today decision</span><strong>{decision}</strong></div>
              <div className="stat-card"><span>Today average gap</span><strong>{selected?.average_gap_percentage ?? "-"}{selected?.average_gap_percentage !== null && selected?.average_gap_percentage !== undefined ? "%" : ""}</strong></div>
              <div className="stat-card"><span>Period average gap</span><strong>{easyDays.period_average_gap_percentage ?? "-"}{easyDays.period_average_gap_percentage !== null ? "%" : ""}</strong></div>
              <div className="stat-card"><span>Favorable days</span><strong>{easyDays.favorable_days} / {easyDays.daily_gaps.length}</strong></div>
              <div className="stat-card"><span>Today average gap</span><strong>{selected?.average_gap_to_leader ?? "-"}{selected?.average_gap_to_leader !== null && selected?.average_gap_to_leader !== undefined ? " s" : ""}</strong></div>
              <div className="stat-card"><span>Period average gap</span><strong>{easyDays.period_average_gap_to_leader ?? "-"}{easyDays.period_average_gap_to_leader !== null ? " s" : ""}</strong></div>
            </div>
            <p className="chart-note">A favorable day has a lower average gap to that day’s fastest pilot than the selected period’s daily average. {consistentPilotsOnly ? `Only pilots active on at least ${easyDays.regular_pilot_threshold} tracked days are averaged (${easyDays.eligible_pilot_count} eligible).` : "All pilots with a recorded time are averaged."}</p>
          </section>
          <section className="panel">
            <div className="panel-header"><div><p className="eyebrow">Daily leader-gap calendar</p><h2>Lower gap means an easier field</h2></div></div>
            <div className="comparison-calendar-list">{Object.entries(months).sort(([left], [right]) => right.localeCompare(left)).map(([month, days]) => {
              const blanks = new Date(`${month}-01T00:00:00`).getDay();
              return <section className="comparison-month" key={month}><h3>{new Date(`${month}-01T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</h3><div className="comparison-weekdays">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((label) => <span key={label}>{label}</span>)}</div><div className="comparison-calendar">{Array.from({ length: blanks }, (_, index) => <span className="comparison-day blank" key={`blank-${index}`} />)}{days.map((day) => <Link to={`/${raceClass}?date=${day.date}&pilot=${encodeURIComponent(selectedPilot)}&general_return=${encodeURIComponent(generalReturnPath)}`} className={`comparison-day comparison-day-link easy-day ${day.is_favorable ? "favorable" : "tough"}`} key={day.date} title={`${day.date}: ${day.average_gap_to_leader ?? "no data"} s average gap`}><small>{day.date.slice(8)}</small><strong>{day.average_gap_to_leader ?? "-"}{day.average_gap_to_leader !== null ? " s" : ""}</strong><em>{day.average_gap_percentage ?? "-"}{day.average_gap_percentage !== null ? "%" : ""} avg gap</em><em>{day.participant_count} pilots</em></Link>)}</div></section>;
            })}</div>
            <p className="chart-note">Green squares are favorable; red squares are above the period average. Each square shows the field’s average seconds behind the day’s leader.</p>
          </section>
        </div>;
      })() : null}
      {dayStreakStats && section === "day-streaks" ? (
        <section className="panel day-streaks-panel">
          <div className="panel-header">
            <div><p className="eyebrow">Day Streaks</p><h2>{dayStreakView === "streaks" ? "Longest consecutive participation" : "Days flown leaderboard"}</h2></div>
            <div className="meta"><span>All-time in the selected class.</span><span>Completed through {dayStreakStats.active_cutoff_date ?? "-"}.</span></div>
          </div>
          <div className="toggle-row day-streak-controls">
            <button type="button" className={dayStreakView === "streaks" ? "chip active" : "chip"} onClick={() => setDayStreakView("streaks")}>Best Streaks</button>
            <button type="button" className={dayStreakView === "days-flown" ? "chip active" : "chip"} onClick={() => setDayStreakView("days-flown")}>Days Flown</button>
            {dayStreakView === "streaks" ? <>
              <span className="control-divider" />
              {(["best", "best-active", "all"] as StreakMode[]).map((mode) => (
                <button type="button" className={streakMode === mode ? "chip active" : "chip"} onClick={() => setStreakMode(mode)} key={mode}>
                  {mode === "best" ? "Best only" : mode === "best-active" ? "Best + active" : "All streaks"}
                </button>
              ))}
              <span className="control-divider" />
              {(["all", "active", "inactive"] as StreakFilter[]).map((filter) => (
                <button type="button" className={streakFilter === filter ? "chip active" : "chip"} onClick={() => setStreakFilter(filter)} key={filter}>
                  {filter === "all" ? "All statuses" : filter[0].toUpperCase() + filter.slice(1)}
                </button>
              ))}
            </> : null}
          </div>

          {dayStreakView === "streaks" ? (
            <div className="streak-leaderboard">
              {visibleStreakRows.length === 0 ? <p>No qualifying streaks match these filters.</p> : null}
              {visibleStreakRows.map((streak, index) => (
                <article className={`streak-leaderboard-row ${streak.is_active ? "streak-active" : "streak-inactive"} ${streak.pilot === selectedPilot ? "selected-row" : ""}`} key={`${streak.pilot}-${streak.start_date}`}>
                  <div className="streak-leaderboard-header">
                    <div><h3>{index + 1}. {streak.pilot}</h3><span className="table-muted">{streak.country ?? "Unknown"}</span></div>
                    <div className="streak-leaderboard-meta"><span>{streak.start_date} to {streak.end_date}</span><strong>{streak.length} days</strong><span className="streak-role">{streak.is_best && streak.is_active ? "Best & Active" : streak.is_best ? "Best" : "Active"}</span></div>
                  </div>
                  <div className="streak-cells">
                    {streak.dates.map((raceDate) => <span className="streak-cell" title={raceDate} key={raceDate} />)}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <>
              <div className="stat-grid days-flown-summary">
                <div className="stat-card"><span>Total pilots</span><strong>{dayStreakStats.days_flown_summary.total_pilots}</strong></div>
                {[7, 10, 20, 30, 50, 100, 200, 300, 400, 500].map((threshold) => (
                  <div className="stat-card" key={threshold}><span>More than {threshold} days</span><strong>{dayStreakStats.days_flown_summary[`more_than_${threshold}_days` as keyof typeof dayStreakStats.days_flown_summary]}</strong></div>
                ))}
              </div>
              <div className="table-scroll">
                <table className="scoreboard">
                  <thead><tr><th>Rank</th><th>Pilot</th><th>Country</th><th>Days flown</th><th>First flight</th><th>Last flight</th></tr></thead>
                  <tbody>{dayStreakStats.days_flown.map((row, index) => (
                    <tr key={row.pilot} className={row.pilot === selectedPilot ? "active-row" : undefined}>
                      <td>{index + 1}</td><td>{row.pilot}</td><td>{row.country ?? "-"}</td><td>{row.days_flown}</td><td>{row.first_flight_date}</td><td>{row.last_flight_date}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </>
          )}
          <p className="chart-note">Streaks require at least three consecutive calendar days. Active means the selected pilot’s best streak reaches the latest completed stored day; inactive streaks are greyed out. Days flown counts one result per race day and excludes today.</p>
        </section>
      ) : null}
      {correlationData && section === "progress-correlation" ? (
        <section className="panel chart-panel progress-correlation-panel">
          <div className="panel-header">
            <div><p className="eyebrow">Progress correlation</p><h2>Experience days versus leader gap</h2></div>
            <label className="field correlation-date-field"><span>Gap data from</span><input type="date" value={correlationFrom} onChange={(event) => setCorrelationFrom(event.target.value)} /></label>
          </div>
          <div className="stat-grid correlation-summary">
            <div className="stat-card"><span>Pilots with valid gaps</span><strong>{correlationData.pilot_count}</strong></div>
            <div className="stat-card"><span>Observations</span><strong>{correlationData.observation_count}</strong></div>
            <div className="stat-card"><span>Pearson correlation</span><strong>{correlationData.pearson_correlation ?? "-"}</strong></div>
            <div className="stat-card"><span>Completed through</span><strong>{correlationData.completed_through ?? "-"}</strong></div>
          </div>
          <div className="chart-actions correlation-controls">
            <label><input type="checkbox" checked={showCorrelationPoints} onChange={() => setShowCorrelationPoints((value) => !value)} /> All pilot observations</label>
            <label><input type="checkbox" checked={showCorrelationAverage} onChange={() => setShowCorrelationAverage((value) => !value)} /> Experience average</label>
            <label><input type="checkbox" checked={showCorrelationViewport} onChange={() => setShowCorrelationViewport((value) => !value)} /> Viewport pilot: {selectedPilot}</label>
          </div>
          <div className="progress-correlation-chart" role="img" aria-label={`Scatter chart of cumulative days flown against percentage gap to the daily top-three average for ${raceClass} class`}>
            <ResponsiveContainer width="100%" height={430}>
              <ComposedChart data={correlationData.points} margin={{ top: 18, right: 24, left: 4, bottom: 18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis type="number" dataKey="days_flown" allowDecimals={false} name="Days flown" label={{ value: "Cumulative days flown", position: "insideBottom", offset: -8 }} />
                <YAxis type="number" dataKey="gap_percentage" unit="%" name="Gap" label={{ value: "Gap to top-3 average (%)", angle: -90, position: "insideLeft" }} />
                <Tooltip content={<CorrelationTooltip />} />
                <Legend />
                {showCorrelationPoints ? <Scatter name="All pilot days" data={correlationData.points} dataKey="gap_percentage" fill="#7aa7ff" fillOpacity={0.35} /> : null}
                {showCorrelationAverage ? <Line name="Average gap by experience" data={correlationData.averages} type="monotone" dataKey="average_gap_percentage" stroke="#ff9d5c" strokeWidth={3} dot={false} connectNulls /> : null}
                {showCorrelationViewport ? <Line name={`${selectedPilot} gap`} data={viewportCorrelationPoints} type="monotone" dataKey="gap_percentage" stroke="#7ef3c5" strokeWidth={3} dot={{ r: 3 }} connectNulls /> : null}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          {viewportCorrelationPoints.length === 0 ? <p className="chart-note">The selected viewport pilot has no valid gap observations in this period.</p> : null}
          <p className="chart-note">Cumulative days flown are counted from the pilot’s first stored result. Gap observations begin on {correlationData.gap_from} and use the daily top-three average as the leader benchmark. A negative correlation suggests the gap tends to shrink as experience grows; early-arriving elite pilots may appear as outliers.</p>
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
