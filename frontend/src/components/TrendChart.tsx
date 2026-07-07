import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { GapPoint } from "../api/types";

export function TrendChart({ data }: { data: GapPoint[] }) {
  return (
    <div className="panel chart-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Performance timeline</p>
          <h2>Leader gap and raw times</h2>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(18, 28, 45, 0.15)" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="pilot_time" stroke="#0d5c63" strokeWidth={3} dot={false} name="Pilot time" />
          <Line
            type="monotone"
            dataKey="leader_average_time"
            stroke="#f28f3b"
            strokeWidth={2}
            dot={false}
            name="Top-3 average"
          />
          <Line
            type="monotone"
            dataKey="field_average_time"
            stroke="#7c9885"
            strokeWidth={2}
            dot={false}
            name="Field average"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
