import { Brush, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { fetchJson } from "../api/client";
import type { PilotStatsResponse, PilotTimelinePoint } from "../api/types";
import { RangeQuickFilters } from "../components/RangeQuickFilters";
import { StreakBoard } from "../components/StreakBoard";
import { usePilot } from "../context/PilotContext";
import { useApi } from "../hooks/useApi";

type PilotSection = "leader-gap" | "logarithmic" | "time-comparison" | "streaks";

const DEFAULT_FROM = "2023-11-15";
const DEFAULT_TO = new Date().toISOString().slice(0, 10);

function buildPilotStatsPath(
  raceClass: string,
  pilot: string,
  dateFrom: string,
  dateTo: string,
  streakThreshold: number,
) {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    streak_threshold: String(streakThreshold),
  });
  return `/analytics/pilot-stats/${raceClass}/${encodeURIComponent(pilot)}?${params.toString()}`;
}

function trimTimeline(points: PilotTimelinePoint[]) {
  const firstIndex = points.findIndex((point) => point.participated);
  return firstIndex >= 0 ? points.slice(firstIndex) : points;
}

function rollingAverage(values: Array<number | null>, windowSize: number) {
  return values.map((_, index) => {
    const windowValues = values.slice(Math.max(0, index - windowSize + 1), index + 1).filter((value): value is number => value !== null);
    if (!windowValues.length) {
      return null;
    }
    return Number((windowValues.reduce((sum, value) => sum + value, 0) / windowValues.length).toFixed(3));
  });
}

export function PilotStatsPage() {
  const { selectedPilot, setSelectedPilot } = usePilot();
  const [searchParams] = useSearchParams();
  const [raceClass, setRaceClass] = useState(searchParams.get("class") ?? "open");
  const [dateFrom, setDateFrom] = useState(searchParams.get("from") ?? DEFAULT_FROM);
  const [dateTo, setDateTo] = useState(searchParams.get("to") ?? DEFAULT_TO);
  const [section, setSection] = useState<PilotSection>("leader-gap");
  const [streakThreshold, setStreakThreshold] = useState(3);
  const [showLeaderAverage, setShowLeaderAverage] = useState(true);
  const [showFieldAverage, setShowFieldAverage] = useState(true);
  const [showPilotTime, setShowPilotTime] = useState(true);
  const [showWeeklyAverage, setShowWeeklyAverage] = useState(false);
  const [showMonthlyAverage, setShowMonthlyAverage] = useState(false);

  useEffect(() => {
    const pilotFromQuery = searchParams.get("pilot");
    if (pilotFromQuery) {
      setSelectedPilot(pilotFromQuery);
    }
  }, [searchParams, setSelectedPilot]);

  const stats = useApi<PilotStatsResponse>(
    () => fetchJson(buildPilotStatsPath(raceClass, selectedPilot, dateFrom, dateTo, streakThreshold)),
    [raceClass, selectedPilot, dateFrom, dateTo, streakThreshold],
  );

  const sectionLabel = {
    "leader-gap": "Leader Gap",
    logarithmic: "Logarithmic View",
    "time-comparison": "Time Comparison",
    streaks: "Day Streaks",
  };

  const handleThresholdChange = (event: ChangeEvent<HTMLInputElement>) => {
    setStreakThreshold(Math.max(3, Number(event.target.value) || 3));
  };

  const leaderGapData = useMemo(() => {
    if (!stats.data) {
      return [];
    }
    const timeline = trimTimeline(stats.data.timeline);
    const gapPercentValues = timeline.map((point) => {
      if (!point.participated || point.pilot_time === null || point.leader_average_time === null || point.leader_average_time === 0) {
        return null;
      }
      return Number((((point.pilot_time - point.leader_average_time) / point.leader_average_time) * 100).toFixed(3));
    });
    const weekly = rollingAverage(gapPercentValues, 7);
    const monthly = rollingAverage(gapPercentValues, 30);
    return timeline.map((point, index) => ({
      date: point.date,
      gap_percent_to_top3: gapPercentValues[index],
      weekly_average_gap_percent: weekly[index],
      monthly_average_gap_percent: monthly[index],
    }));
  }, [stats.data]);

  return (
    <div className="stack">
      <section className="panel hero-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Pilot stats</p>
            <h2>{selectedPilot}</h2>
          </div>
          <div className="meta">
            <span>Daily charts read from the stored database, not from the source site API.</span>
            <span>Stats date range only affects analytics below.</span>
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
          <label className="field">
            <span>Streak threshold</span>
            <input type="number" min={3} value={streakThreshold} onChange={handleThresholdChange} />
          </label>
        </div>

        <RangeQuickFilters onApply={(from, to) => { setDateFrom(from); setDateTo(to); }} />

        <div className="section-tabs">
          {Object.entries(sectionLabel).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={section === value ? "chip active" : "chip"}
              onClick={() => setSection(value as PilotSection)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {stats.loading ? <div className="panel">Loading pilot stats...</div> : null}
      {stats.error ? <div className="panel">Pilot stats unavailable: {stats.error}</div> : null}

      {stats.data && section === "leader-gap" ? (
        <section className="panel chart-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Leader gap</p>
              <h2>Gap to top-3 average (%)</h2>
            </div>
            <div className="toggle-row">
              <label><input type="checkbox" checked={showWeeklyAverage} onChange={() => setShowWeeklyAverage((value) => !value)} /> Weekly average (%)</label>
              <label><input type="checkbox" checked={showMonthlyAverage} onChange={() => setShowMonthlyAverage((value) => !value)} /> Monthly average (%)</label>
            </div>
          </div>
          <div className="chart-actions">
            <span className="chart-hint">Use the brush below to zoom and inspect a time sector.</span>
          </div>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={leaderGapData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="date" />
              <YAxis unit="%" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="gap_percent_to_top3" stroke="#7ef3c5" strokeWidth={2.5} connectNulls={false} name="Gap to top-3 avg (%)" />
              {showWeeklyAverage ? <Line type="monotone" dataKey="weekly_average_gap_percent" stroke="#ff9d5c" strokeWidth={2} dot={false} name="Weekly avg gap (%)" /> : null}
              {showMonthlyAverage ? <Line type="monotone" dataKey="monthly_average_gap_percent" stroke="#ffe072" strokeWidth={2} dot={false} name="Monthly avg gap (%)" /> : null}
              <Brush dataKey="date" height={24} stroke="#7ef3c5" travellerWidth={10} />
            </LineChart>
          </ResponsiveContainer>
          <p className="chart-note">
            The main line shows how far the pilot was from the average of the top 3 times, expressed as a percentage of that average. Weekly and monthly lines are rolling averages over the visible history.
          </p>
        </section>
      ) : null}

      {stats.data && section === "logarithmic" ? (
        <section className="panel chart-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Pilot stats</p>
              <h2>Logarithmic score and leader gap</h2>
            </div>
          </div>
          <div className="chart-actions">
            <span className="chart-hint">Use the brush below to zoom and inspect a time sector.</span>
          </div>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={stats.data.active_timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" domain={[0, 100]} unit="%" />
              <YAxis yAxisId="right" orientation="right" unit="s" />
              <Tooltip />
              <Legend />
              <Line type="monotone" yAxisId="left" dataKey="normalized_score" stroke="#ffe072" strokeWidth={3} name="Normalized score (%)" />
              <Line type="monotone" yAxisId="right" dataKey="gap_to_leader" stroke="#7ef3c5" strokeWidth={2} name="Gap to leader (s)" />
              <Brush dataKey="date" height={24} stroke="#7ef3c5" travellerWidth={10} />
            </LineChart>
          </ResponsiveContainer>
          <p className="chart-note">
            Normalized score is the pilot’s position between the day’s fastest and slowest recorded time, scaled to 0-100%. Gap to leader shows the raw time deficit in seconds.
          </p>
        </section>
      ) : null}

      {stats.data && section === "time-comparison" ? (
        <section className="panel chart-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Pilot stats</p>
              <h2>Top-3 average, pilot time, and field average</h2>
            </div>
            <div className="toggle-row">
              <label><input type="checkbox" checked={showPilotTime} onChange={() => setShowPilotTime((value) => !value)} /> Pilot time</label>
              <label><input type="checkbox" checked={showLeaderAverage} onChange={() => setShowLeaderAverage((value) => !value)} /> Top-3 average</label>
              <label><input type="checkbox" checked={showFieldAverage} onChange={() => setShowFieldAverage((value) => !value)} /> Field average</label>
            </div>
          </div>
          <div className="chart-actions">
            <span className="chart-hint">Use the brush below to zoom and inspect a time sector.</span>
          </div>
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={stats.data.active_timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="date" />
              <YAxis unit="s" />
              <Tooltip />
              <Legend />
              {showPilotTime ? <Line type="monotone" dataKey="pilot_time" stroke="#7ef3c5" strokeWidth={3} name="Pilot time (s)" /> : null}
              {showLeaderAverage ? <Line type="monotone" dataKey="leader_average_time" stroke="#ff9d5c" strokeWidth={2} name="Top-3 average (s)" /> : null}
              {showFieldAverage ? <Line type="monotone" dataKey="field_average_time" stroke="#ffe072" strokeWidth={2} name="Field average (s)" /> : null}
              <Brush dataKey="date" height={24} stroke="#7ef3c5" travellerWidth={10} />
            </LineChart>
          </ResponsiveContainer>
          <p className="chart-note">
            This chart compares the selected pilot’s raw time against the top-3 average and the field average for each day the pilot flew. Dates without a flight are omitted here.
          </p>
        </section>
      ) : null}

      {stats.data && section === "streaks" ? <StreakBoard streaks={stats.data.streaks} /> : null}
    </div>
  );
}
