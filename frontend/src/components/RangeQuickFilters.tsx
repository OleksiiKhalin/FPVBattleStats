type Props = {
  onApply: (from: string, to: string) => void;
  onClear: () => void;
  seasons?: string[];
  season?: string;
  onSeasonChange?: (season: string) => void;
};

function formatDate(value: Date) {
  return value.toISOString().slice(0, 10);
}

function shiftDays(days: number) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return { from: formatDate(start), to: formatDate(end) };
}

export function RangeQuickFilters({ onApply, onClear, seasons = [], season = "", onSeasonChange }: Props) {
  const options = [
    { label: "Last week", days: 7 },
    { label: "Last month", days: 30 },
    { label: "Last quarter", days: 90 },
    { label: "Last year", days: 365 },
  ];

  return (
    <div className="quick-filters">
      {options.map((option) => (
        <button
          key={option.label}
          type="button"
          className="chip"
          onClick={() => {
            const range = shiftDays(option.days);
            onApply(range.from, range.to);
          }}
        >
          {option.label}
        </button>
      ))}
      {seasons[0] ? <button type="button" className="chip" onClick={() => onSeasonChange?.(seasons[0])}>Current season</button> : null}
      <button type="button" className="chip" onClick={onClear}>Clear dates</button>
      {onSeasonChange ? (
        <label className="scope-filter">
          <span>Statistics scope</span>
          <select value={season} onChange={(event) => onSeasonChange(event.target.value)}>
            <option value="">All dates</option>
            {[...seasons].sort((left, right) => right.localeCompare(left)).map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
      ) : null}
    </div>
  );
}