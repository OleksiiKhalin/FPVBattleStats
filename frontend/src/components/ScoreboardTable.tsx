import { useState } from "react";
import { Link } from "react-router-dom";

import { fetchJson } from "../api/client";
import type { PilotHoverCardResponse, ScoreboardEntry, ScoreboardResponse } from "../api/types";
import { usePilot } from "../context/PilotContext";
import { PilotHoverCard } from "./PilotHoverCard";

type Props = {
  data: ScoreboardResponse;
  selectedDate: string;
};

type HoverState = {
  pilot: string;
  x: number;
  y: number;
  data: PilotHoverCardResponse | null;
};

function groupRows(rows: ScoreboardEntry[]) {
  const groups = new Map<string, ScoreboardEntry[]>();
  for (const row of rows) {
    const key = row.category ?? "Overall";
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(row);
  }
  return [...groups.entries()];
}

function formatTime(value: number | null) {
  return value === null ? "-" : value.toFixed(3);
}

export function ScoreboardTable({ data, selectedDate }: Props) {
  const { selectedPilot, setSelectedPilot } = usePilot();
  const [hoverState, setHoverState] = useState<HoverState | null>(null);
  const groups = groupRows(data.rows);

  const loadHoverCard = async (pilot: string, x: number, y: number) => {
    setHoverState({ pilot, x, y, data: null });
    try {
      const payload = await fetchJson<PilotHoverCardResponse>(
        `/analytics/pilot-hover/${data.race_class}/${encodeURIComponent(pilot)}?target_date=${selectedDate}`,
      );
      setHoverState((current) => (current && current.pilot === pilot ? { ...current, data: payload } : current));
    } catch {
      setHoverState(null);
    }
  };

  return (
    <section className="panel scoreboard-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{data.season} / {data.race_class}</p>
          <h2>{data.track}</h2>
        </div>
        <div className="meta">
          <span>{data.date}</span>
          <span>{data.quad_of_the_day ? `Quad of the Day: ${data.quad_of_the_day}` : "No quad restriction"}</span>
        </div>
      </div>

      <div className="leaderboard-groups">
        {groups.map(([groupName, rows]) => (
          <article key={groupName} className="leaderboard-group">
            <div className="group-title-row">
              <h3>{groupName}</h3>
              <span>{rows.length} pilots</span>
            </div>
            <table className="scoreboard compact-scoreboard fixed-scoreboard">
              <colgroup>
                <col style={{ width: "8%" }} />
                <col style={{ width: "30%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "28%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "10%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Pilot</th>
                  <th>Country</th>
                  <th>Quad</th>
                  <th>Time</th>
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={`${groupName}-${row.pilot}-${row.place ?? "na"}`}
                    className={row.pilot === selectedPilot ? "active-row" : undefined}
                    onMouseEnter={(event) => {
                      if (row.pilot !== selectedPilot) {
                        void loadHoverCard(row.pilot, event.clientX, event.clientY);
                      }
                    }}
                    onMouseMove={(event) => {
                      setHoverState((current) => (current ? { ...current, x: event.clientX, y: event.clientY } : current));
                    }}
                    onMouseLeave={() => setHoverState(null)}
                  >
                    <td>{row.place ?? "-"}</td>
                    <td>
                      <Link
                        to={`/pilot-stats?class=${data.race_class}&pilot=${encodeURIComponent(row.pilot)}`}
                        onClick={() => setSelectedPilot(row.pilot)}
                      >
                        {row.pilot}
                      </Link>
                    </td>
                    <td>{row.country ?? "-"}</td>
                    <td>{row.quad ?? "-"}</td>
                    <td>{formatTime(row.time)}</td>
                    <td>{row.points ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
      </div>

      {hoverState?.data ? <PilotHoverCard data={hoverState.data} x={hoverState.x} y={hoverState.y} /> : null}
    </section>
  );
}
