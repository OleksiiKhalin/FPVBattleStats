import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { PilotHoverCardResponse } from "../api/types";

type Props = {
  data: PilotHoverCardResponse;
  x: number;
  y: number;
};

export function PilotHoverCard({ data, x, y }: Props) {
  return (
    <div
      className="hover-card"
      style={{
        left: Math.min(x + 18, window.innerWidth - 340),
        top: Math.min(y + 18, window.innerHeight - 320),
      }}
    >
      <div className="hover-card-header">
        <div>
          <p className="eyebrow">Current season</p>
          <h3>{data.pilot}</h3>
        </div>
        <div className="meta">
          <span>{data.season}</span>
          <span>Skipped: {data.skipped_days}</span>
        </div>
      </div>
      <div className="hover-chart-block">
        <p className="hover-chart-title">Skipped days</p>
        <ResponsiveContainer width="100%" height={90}>
          <BarChart data={data.timeline}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="date" hide />
            <YAxis hide />
            <Tooltip />
            <Bar dataKey="skipped" fill="#ff9d5c" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="hover-chart-block">
        <p className="hover-chart-title">Places</p>
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={data.timeline}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="date" hide />
            <YAxis reversed domain={[1, "dataMax + 1"]} />
            <Tooltip />
            <Bar dataKey="place" fill="#7ef3c5" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
