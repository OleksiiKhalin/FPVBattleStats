import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fetchJson } from "../api/client";
import type { PilotSeasonPlaceSummary, PilotStatsResponse } from "../api/types";
import { useApi } from "../hooks/useApi";
import { PilotComparisonPicker } from "./PilotComparisonPicker";

type Props = {
  seasons: PilotSeasonPlaceSummary[];
  raceClass: string;
  pilotName: string;
  opponentPilot: string;
  onOpponentChange: (pilot: string) => void;
};

type ChartPoint = PilotSeasonPlaceSummary["places"][number] & { bar_height: number };

const MAX_BAR_HEIGHT = 100;
const leagueLabels: Record<string, string> = {
  gold: "Gold",
  silver: "Silver",
  bronze: "Bronze",
  unranked: "Unranked",
};

function monthLabel(value: string) {
  return new Date(`${value}-01T00:00:00`).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function formatPlace(value: number | null) {
  return value === null ? "-" : Number(value.toFixed(2));
}

function leagueLabel(value: string | null) {
  return value ? leagueLabels[value] ?? value : "Unranked";
}

function leagueClass(value: string | null) {
  return `league-pill league-${value ?? "unranked"}`;
}

function medalFor(season: PilotSeasonPlaceSummary) {
  if (!season.is_complete) return null;
  if (season.season_place === 1) return "🥇";
  if (season.season_place === 2) return "🥈";
  if (season.season_place === 3) return "🥉";
  return null;
}

function buildTickPlaces(minPlace: number, maxPlace: number) {
  const range = maxPlace - minPlace + 1;
  if (range <= 12) return Array.from({ length: range }, (_, index) => minPlace + index);
  const step = Math.ceil(range / 10);
  const places = new Set([minPlace, maxPlace]);
  for (let place = minPlace + step; place < maxPlace; place += step) places.add(place);
  return [...places].sort((left, right) => left - right);
}

function buildPilotStatsPath(raceClass: string, pilotName: string) {
  return `/analytics/pilot-stats/${raceClass}/${encodeURIComponent(pilotName)}?streak_threshold=3`;
}

function placeColor(place: number) {
  if (place === 1) return "#ffe072";
  if (place === 2) return "#c8d0dc";
  if (place === 3) return "#cf8a5a";
  return "#7ef3c5";
}

type PlaceChartProps = {
  pilotName: string;
  raceClass: string;
  points: PilotSeasonPlaceSummary["places"];
  minPlace: number;
  maxPlace: number;
};

function PlaceChart({ pilotName, raceClass, points, minPlace, maxPlace }: PlaceChartProps) {
  const navigate = useNavigate();
  const placeRange = maxPlace - minPlace + 1;
  const logRange = Math.log(placeRange + 1);
  const chartData = useMemo<ChartPoint[]>(() => points.map((point) => ({
    ...point,
    bar_height: MAX_BAR_HEIGHT * (logRange - Math.log(point.place - minPlace + 1)) / logRange,
  })), [logRange, minPlace, points]);
  const tickPlaces = buildTickPlaces(minPlace, maxPlace);
  const tickValues = tickPlaces.map((place) => MAX_BAR_HEIGHT * (logRange - Math.log(place - minPlace + 1)) / logRange);

  const openLeaderboard = (point: ChartPoint) => {
    const params = new URLSearchParams({ date: point.date, pilot: pilotName });
    navigate(`/${raceClass}?${params.toString()}`);
  };

  return (
    <section className="place-chart-section" aria-label={`${pilotName} places chart`}>
      <div className="place-chart-heading">
        <div>
          <p className="eyebrow">Daily places</p>
          <h3>{pilotName}</h3>
        </div>
        <span className="chart-hint">Best observed place: {minPlace}; fixed maximum bar height: {MAX_BAR_HEIGHT}</span>
      </div>
      {chartData.length === 0 ? (
        <p className="empty-state">{pilotName} has no ranked daily places in this season.</p>
      ) : (
        <ResponsiveContainer width="100%" height={360}>
          <BarChart data={chartData} margin={{ top: 20, right: 12, left: 4, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="date" />
            <YAxis
              domain={[0, MAX_BAR_HEIGHT]}
              ticks={tickValues}
              allowDecimals={false}
              tickFormatter={(value) => String(Math.round(Math.exp(logRange * (1 - Number(value) / MAX_BAR_HEIGHT)) + minPlace - 1))}
              label={{ value: "Place (1 = best)", angle: -90, position: "insideLeft" }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const point = payload[0].payload as ChartPoint;
                return (
                  <div className="chart-tooltip">
                    <strong>{point.date}</strong>
                    <span>{pilotName}</span>
                    <span>Place: {point.place}</span>
                  </div>
                );
              }}
            />
            <Bar
              dataKey="bar_height"
              name={`${pilotName} place performance`}
              radius={[4, 4, 0, 0]}
              cursor="pointer"
              onClick={(data) => {
                const point = (data as { payload?: ChartPoint }).payload;
                if (point) openLeaderboard(point);
              }}
            >
              <LabelList dataKey="place" position="top" fill="#f4efe6" />
              {chartData.map((point) => <Cell key={`${point.date}-${point.place}`} fill={placeColor(point.place)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

export function PilotPlacesPanel({ seasons, raceClass, pilotName, opponentPilot, onOpponentChange }: Props) {
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const selected = seasons.find((season) => season.season === selectedSeason) ?? null;
  const opponentStats = useApi<PilotStatsResponse>(
    () => fetchJson(buildPilotStatsPath(raceClass, opponentPilot)),
    [raceClass, opponentPilot],
    Boolean(selected && opponentPilot),
  );
  const opponentSeason = opponentStats.data?.place_seasons.find((season) => season.season === selectedSeason) ?? null;
  const allSelectedPlaces = useMemo(
    () => [...(selected?.places ?? []), ...(opponentSeason?.places ?? [])].map((point) => point.place),
    [opponentSeason, selected],
  );
  const minPlace = allSelectedPlaces.length ? Math.min(...allSelectedPlaces) : 1;
  const maxPlace = allSelectedPlaces.length ? Math.max(...allSelectedPlaces) : 1;

  useEffect(() => {
    if (selectedSeason && !seasons.some((season) => season.season === selectedSeason)) setSelectedSeason(null);
  }, [seasons, selectedSeason]);

  return (
    <section className="panel places-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Places</p>
          <h2>Season results</h2>
        </div>
        <span className="chart-hint">Average place uses ranked daily results. League is calculated before each Open season.</span>
      </div>

      <PilotComparisonPicker primaryPilot={pilotName} raceClass={raceClass} value={opponentPilot} onChange={onOpponentChange} />

      {seasons.length === 0 ? <p className="empty-state">This pilot has no recorded seasons in this class.</p> : null}
      <div className="place-season-grid">
        {seasons.map((season) => {
          const medal = medalFor(season);
          const isSelected = season.season === selectedSeason;
          return (
            <button
              key={season.season}
              type="button"
              className={isSelected ? "place-season-card active" : "place-season-card"}
              aria-pressed={isSelected}
              onClick={() => setSelectedSeason((current) => current === season.season ? null : season.season)}
            >
              <span className="place-season-card-header">
                <strong>{monthLabel(season.season)}</strong>
                {medal ? <span className="season-medal" aria-label={`Final season place ${season.season_place}`}>{medal}</span> : null}
              </span>
              <span className="place-season-card-meta">
                <span>Average place <strong>{formatPlace(season.average_place)}</strong></span>
                {raceClass === "open" ? <span className={leagueClass(season.league)}>{leagueLabel(season.league)}</span> : <span className="no-league">No league</span>}
              </span>
              <span className="place-season-card-status">{season.is_complete ? "Completed season" : "Season in progress"}</span>
            </button>
          );
        })}
      </div>

      {selected ? (
        <div className="place-chart-wrap">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Selected season</p>
              <h3>{monthLabel(selected.season)} places</h3>
            </div>
            <span className="chart-hint">Both charts share the observed place range. Labels and tooltips show the original integer place.</span>
          </div>
          <div className="place-comparison-charts">
            <PlaceChart pilotName={pilotName} raceClass={raceClass} points={selected.places} minPlace={minPlace} maxPlace={maxPlace} />
            {opponentStats.loading ? <p className="empty-state place-comparison-status">Loading {opponentPilot} places...</p> : null}
            {opponentStats.error ? <p className="empty-state place-comparison-status">Comparison places unavailable: {opponentStats.error}</p> : null}
            {!opponentStats.loading && !opponentStats.error && opponentPilot ? <PlaceChart pilotName={opponentPilot} raceClass={raceClass} points={opponentSeason?.places ?? []} minPlace={minPlace} maxPlace={maxPlace} /> : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
