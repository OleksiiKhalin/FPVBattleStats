import type { PilotStatsResponse } from "../api/types";

export function StreakBoard({ streaks }: { streaks: PilotStatsResponse["streaks"] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Consistency</p>
          <h2>Streak history</h2>
        </div>
        <div className="meta">
          <span>Threshold: {streaks.threshold}+ days</span>
          <span>Singles: {streaks.lonely_single_days}</span>
          <span>Two-day runs: {streaks.lonely_two_day_runs}</span>
        </div>
      </div>

      <div className="streak-groups">
        {streaks.streaks.length === 0 ? <p>No streaks hit the selected threshold.</p> : null}
        {streaks.streaks.map((streak) => (
          <article key={`${streak.start_date}-${streak.end_date}`} className="streak-group">
            <h3>
              {streak.start_date} to {streak.end_date} ({streak.length} days)
            </h3>
            <div className="streak-cells">
              {streak.dates.map((raceDate) => (
                <span key={raceDate} className="streak-cell" title={raceDate} />
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
