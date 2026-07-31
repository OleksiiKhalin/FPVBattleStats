import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { fetchJson } from "../api/client";
import type { PilotComparisonDay, PilotComparisonResponse, PilotOption } from "../api/types";
import { useApi } from "../hooks/useApi";

type Props = {
  primaryPilot: string;
  raceClass: string;
  dateFrom: string;
  dateTo: string;
};

const RECENT_PILOTS_KEY = "fpvbattle-recent-comparison-pilots";

function buildComparisonPath(raceClass: string, primaryPilot: string, opponentPilot: string, dateFrom: string, dateTo: string) {
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  return `/analytics/pilot-compare/${raceClass}/${encodeURIComponent(primaryPilot)}/${encodeURIComponent(opponentPilot)}?${params.toString()}`;
}

function formatNumber(value: number | null, suffix = "") {
  return value === null ? "-" : `${value}${suffix}`;
}

function formatGapDifference(primaryGap: number | null, opponentGap: number | null) {
  if (primaryGap === null || opponentGap === null || opponentGap === 0) return "-";
  return `${Number((((primaryGap - opponentGap) / opponentGap) * 100).toFixed(1))}%`;
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
      <p className="eyebrow average-place-heading">Average place</p>
      <div className="league-places">
        {Object.entries(stats.average_place_by_category).map(([league, averagePlace]) => (
          <span key={league}>{league}: <strong>{formatNumber(averagePlace)}</strong></span>
        ))}
      </div>

    </section>
  );
}

function readRecentPilots() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_PILOTS_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

export function PilotComparisonPanel({ primaryPilot, raceClass, dateFrom, dateTo }: Props) {
  const [opponentPilot, setOpponentPilot] = useState("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [recentPilots, setRecentPilots] = useState<string[]>(readRecentPilots);
  const [showCalendarGaps, setShowCalendarGaps] = useState(true);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const pilots = useApi<PilotOption[]>(() => fetchJson(`/analytics/pilots?race_class=${raceClass}`), [raceClass]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const firstPilot = pilots.data?.find((pilot) => pilot.pilot !== primaryPilot)?.pilot ?? "";
    setOpponentPilot((current) => current && current !== primaryPilot && pilots.data?.some((pilot) => pilot.pilot === current) ? current : firstPilot);
  }, [pilots.data, primaryPilot, raceClass]);

  useEffect(() => {
    setQuery(opponentPilot);
  }, [opponentPilot]);

  const options = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (pilots.data ?? [])
      .filter((pilot) => pilot.pilot !== primaryPilot)
      .filter((pilot) => !normalized || pilot.pilot.toLowerCase().includes(normalized) || (pilot.country ?? "").toLowerCase().includes(normalized))
      .slice(0, 24);
  }, [pilots.data, primaryPilot, query]);

  const selectOpponent = (pilot: string) => {
    setOpponentPilot(pilot);
    setQuery(pilot);
    setOpen(false);
    const nextRecent = [pilot, ...recentPilots.filter((value) => value !== pilot && value !== primaryPilot)].slice(0, 5);
    setRecentPilots(nextRecent);
    localStorage.setItem(RECENT_PILOTS_KEY, JSON.stringify(nextRecent));
  };

  const comparison = useApi<PilotComparisonResponse>(
    () => fetchJson(buildComparisonPath(raceClass, primaryPilot, opponentPilot, dateFrom, dateTo)),
    [raceClass, primaryPilot, opponentPilot, dateFrom, dateTo],
  );

  const months = useMemo(() => {
    const grouped = new Map<string, PilotComparisonDay[]>();
    for (const day of comparison.data?.days ?? []) {
      const month = day.date.slice(0, 7);
      grouped.set(month, [...(grouped.get(month) ?? []), day]);
    }
    return [...grouped.entries()].sort(([left], [right]) => right.localeCompare(left));
  }, [comparison.data]);

  const comparisonInsights = useMemo(() => {
    const shared = (comparison.data?.days ?? []).filter((day) => day.difference_seconds !== null);
    const tightDays = shared.filter((day) => Math.abs(day.difference_seconds ?? 0) <= 0.5).length;
    const skippedByPrimary = (comparison.data?.days ?? []).filter((day) => day.primary_time === null && day.opponent_time !== null).length;
    const skippedByOpponent = (comparison.data?.days ?? []).filter((day) => day.primary_time !== null && day.opponent_time === null).length;
    const largestPlaceGap = Math.max(0, ...shared.map((day) => Math.abs((day.primary_place ?? 0) - (day.opponent_place ?? 0))));
    return { tightDays, skippedByPrimary, skippedByOpponent, largestPlaceGap };
  }, [comparison.data]);
  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-header"><div><p className="eyebrow">Head-to-head</p><h2>Compare {primaryPilot} against another pilot</h2></div><div className="meta"><span>Statistics use the selected class and date scope.</span></div></div>
        <div className="comparison-controls"><div className="comparison-picker" ref={rootRef}>
          <label className="field"><span>Compare with</span>
            <div className="combo-box">
              <input value={query} onFocus={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onKeyDown={(event) => { if (event.key === "Enter" && options[0]) { event.preventDefault(); selectOpponent(options[0].pilot); } }} placeholder="Search pilot name" autoComplete="off" />
              <button type="button" className="combo-toggle" onClick={() => setOpen((value) => !value)}>v</button>
              {open ? <div className="combo-menu">{options.length === 0 ? <div className="combo-empty">No pilots found</div> : options.map((pilot) => <button key={pilot.pilot} type="button" className={pilot.pilot === opponentPilot ? "combo-option active" : "combo-option"} onClick={() => selectOpponent(pilot.pilot)}><span>{pilot.pilot}</span><small>{pilot.country ?? "Unknown"}</small></button>)}</div> : null}
            </div>
          </label>
        </div>
        {recentPilots.filter((pilot) => pilot !== primaryPilot).length ? <div className="quick-filters recent-pilots"><span>Recent pilots</span>{recentPilots.filter((pilot) => pilot !== primaryPilot).map((pilot) => <button className={pilot === opponentPilot ? "chip active" : "chip"} type="button" key={pilot} onClick={() => selectOpponent(pilot)}>{pilot}</button>)}</div> : null}</div>
      </section>

      {comparison.loading ? <div className="panel">Loading comparison...</div> : null}
      {comparison.error ? <div className="panel">Comparison unavailable: {comparison.error}</div> : null}
      {comparison.data ? <>
        <section className="panel"><div className="panel-header"><div><p className="eyebrow">Shared race days</p><h2>Matchup KPIs</h2></div></div><div className="stat-grid comparison-kpis"><div className="stat-card"><span>{primaryPilot} win rate</span><strong>{formatNumber(comparison.data.win_rate, "%")}</strong></div><div className="stat-card"><span>Wins / shared days</span><strong>{comparison.data.primary_wins} / {comparison.data.shared_days}</strong></div><div className="stat-card"><span>Gap-to-leader difference</span><strong className={comparison.data.primary.average_gap_to_leader !== null && comparison.data.opponent.average_gap_to_leader !== null && comparison.data.primary.average_gap_to_leader < comparison.data.opponent.average_gap_to_leader ? "gap-better" : "gap-worse"}>{formatGapDifference(comparison.data.primary.average_gap_to_leader, comparison.data.opponent.average_gap_to_leader)}</strong></div></div></section>
        <section className="panel comparison-pilots"><PilotSummary name={primaryPilot} stats={comparison.data.primary} /><PilotSummary name={opponentPilot} stats={comparison.data.opponent} /></section>
        <section className="panel"><div className="panel-header"><div><p className="eyebrow">Why this matchup swings</p><h2>Race-day factors</h2></div></div><div className="stat-grid comparison-kpis"><div className="stat-card"><span>Tight battles</span><strong>{comparisonInsights.tightDays} / {comparison.data.shared_days}</strong></div><div className="stat-card"><span>Largest place difference</span><strong>{comparisonInsights.largestPlaceGap || "-"}</strong></div><div className="stat-card"><span>One-pilot skips</span><strong>{comparisonInsights.skippedByPrimary + comparisonInsights.skippedByOpponent}</strong></div></div><p className="chart-note">Tight battles are shared days within 0.5 seconds. Skips count days only one pilot flew; place difference shows the widest gap on a shared day.</p></section><section className="panel"><div className="panel-header"><div><p className="eyebrow">Daily results</p><h2>Monthly head-to-head calendar</h2></div><label className="toggle-row"><input type="checkbox" checked={showCalendarGaps} onChange={() => setShowCalendarGaps((value) => !value)} /> Show leader gaps</label></div><div className="comparison-calendar-list">{months.map(([month, days]) => { const leadingBlanks = new Date(`${month}-01T00:00:00`).getDay(); return <section className="comparison-month" key={month}><h3>{monthLabel(month)}</h3><div className="comparison-weekdays">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((label) => <span key={label}>{label}</span>)}</div><div className="comparison-calendar">{Array.from({ length: leadingBlanks }, (_, index) => <span className="comparison-day blank" key={`blank-${index}`} />)}{days.map((day) => <div className={day.difference_seconds === null ? "comparison-day missing" : "comparison-day"} style={comparisonTileStyle(day)} key={day.date} title={day.date}><Link to={`/${raceClass}?date=${day.date}`} className="comparison-day-link"><small>{day.date.slice(8)}</small><strong>{day.difference_seconds === null ? "-" : `${day.difference_seconds > 0 ? "-" : "+"}${Math.abs(day.difference_seconds)}s`}</strong>{showCalendarGaps ? <em>{primaryPilot}: {formatNumber(day.primary_gap_to_leader, "s")} · {opponentPilot}: {formatNumber(day.opponent_gap_to_leader, "s")}</em> : null}</Link></div>)}</div></section>; })}</div><p className="chart-note">Each square shows the seconds difference: positive green means {primaryPilot} was faster, while negative red means they were slower. Stronger colour means a larger percentage difference. Black squares show days when at least one pilot did not fly.</p></section>
      </> : null}
    </div>
  );
}