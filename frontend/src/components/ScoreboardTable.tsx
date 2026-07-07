import { Link } from "react-router-dom";

import type { ScoreboardResponse } from "../api/types";
import { usePilot } from "../context/PilotContext";

type Props = {
  data: ScoreboardResponse;
};

export function ScoreboardTable({ data }: Props) {
  const { selectedPilot, setSelectedPilot } = usePilot();

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{data.season}</p>
          <h2>{data.track}</h2>
        </div>
        <div className="meta">
          <span>{data.date}</span>
          <span>{data.quad_of_the_day ? `Quad of the Day: ${data.quad_of_the_day}` : "No quad restriction"}</span>
        </div>
      </div>

      <table className="scoreboard">
        <thead>
          <tr>
            <th>Place</th>
            <th>Pilot</th>
            <th>Category</th>
            <th>Quad</th>
            <th>Time</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr
              key={`${row.pilot}-${row.place ?? "na"}`}
              className={row.pilot === selectedPilot ? "active-row" : undefined}
            >
              <td>{row.place ?? "-"}</td>
              <td>
                <Link
                  to={`/analytics/${data.race_class}?pilot=${encodeURIComponent(row.pilot)}`}
                  onClick={() => setSelectedPilot(row.pilot)}
                >
                  {row.pilot}
                </Link>
              </td>
              <td>{row.category ?? "-"}</td>
              <td>{row.quad ?? "-"}</td>
              <td>{row.time ?? "-"}</td>
              <td>{row.points ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
