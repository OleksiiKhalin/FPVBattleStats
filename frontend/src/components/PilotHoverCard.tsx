import { createPortal } from "react-dom";

import type { PilotHoverCardResponse } from "../api/types";

type Props = {
  data: PilotHoverCardResponse;
  x: number;
  y: number;
};

const CARD_WIDTH = 320;
const CARD_HEIGHT = 248;
const EDGE = 12;

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value}%`;
}

export function PilotHoverCard({ data, x, y }: Props) {
  const left = Math.max(EDGE, Math.min(x + 16, window.innerWidth - CARD_WIDTH - EDGE));
  const top = Math.max(EDGE, Math.min(y + 16, window.innerHeight - CARD_HEIGHT - EDGE));
  return createPortal(
    <aside className="hover-card" style={{ left, top }}>
      <div className="hover-card-header">
        <div><p className="eyebrow">Season to {data.target_date}</p><h3>{data.pilot}</h3></div>
        <div className="meta"><span>{data.season}</span><span>Skipped: {data.skipped_days}</span></div>
      </div>
      <div className="hover-kpis">
        <span>Season points <strong>{data.season_points ?? "-"}</strong></span>
        <span>Average place <strong>{data.average_place ?? "-"}</strong></span>
        <span>Season wins <strong>{data.season_wins} / {data.appearances}</strong></span>
        <span>Season win rate <strong>{formatPercent(data.season_win_rate)}</strong></span>
        <span>Vs viewpoint <strong>{data.wins_against_viewpoint} / {data.shared_days_with_viewpoint}</strong></span>
        <span>Vs viewpoint win rate <strong>{formatPercent(data.win_rate_against_viewpoint)}</strong></span>
      </div>
      <p className="chart-note">Points and season statistics include results through the viewed leaderboard date.</p>
    </aside>,
    document.body,
  );
}