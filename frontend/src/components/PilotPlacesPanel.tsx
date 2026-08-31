import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { PilotSeasonPlaceSummary } from "../api/types";

type Props = {
  seasons: PilotSeasonPlaceSummary[];
};

type ChartPoint = PilotSeasonPlaceSummary["places"][number] & { bar_height: number };

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

function buildTickPlaces(maxPlace: number) {
  if (maxPlace <= 12) return Array.from({ length: maxPlace }, (_, index) => index + 1);
  const step = Math.ceil(maxPlace / 10);
  const places = new Set([1, maxPlace]);
  for (let place = 1 + step; place < maxPlace; place += step) places.add(place);
  return [...places].sort((left, right) => left - right);
}

export function PilotPlacesPanel({ seasons }: Props) {
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const selected = seasons.find((season) => season.season === selectedSeason) ?? null;
  const maxPlace = selected ? Math.max(...selected.places.map((point) => point.place), 1) : 1;
  const maxBarHeight = Math.log(maxPlace + 1) - Math.log(1);
  const chartData = useMemo<ChartPoint[]>(() => {
    if (!selected) return [];
    return selected.places.map((point) => ({
      ...point,
      bar_height: maxBarHeight - Math.log(point.place),
    }));
  }, [maxBarHeight, selected]);
  const tickPlaces = buildTickPlaces(maxPlace);
  const tickValues = tickPlaces.map((place) => maxBarHeight - Math.log(place));

  return (
    <section className="panel places-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Places</p>
          <h2>Season results</h2>
        </div>
        <span className="chart-hint">Average place uses ranked daily results. League is calculated before each season.</span>
      </div>

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
                <span className={leagueClass(season.league)}>{leagueLabel(season.league)}</span>
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
            <span className="chart-hint">Higher bars represent better places; the tooltip shows the integer place.</span>
          </div>
          {chartData.length === 0 ? (
            <p className="empty-state">No ranked daily places were recorded for this season.</p>
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={chartData} margin={{ top: 12, right: 12, left: 4, bottom: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="date" />
                <YAxis
                  domain={[0, "auto"]}
                  ticks={tickValues}
                  allowDecimals={false}
                  tickFormatter={(value) => String(Math.round((maxPlace + 1) / Math.exp(Number(value))))}
                  label={{ value: "Place (1 = best)", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const point = payload[0].payload as ChartPoint;
                    return (
                      <div className="chart-tooltip">
                        <strong>{point.date}</strong>
                        <span>Place: {point.place}</span>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="bar_height" fill="#7ef3c5" name="Place performance" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      ) : null}
    </section>
  );
}
