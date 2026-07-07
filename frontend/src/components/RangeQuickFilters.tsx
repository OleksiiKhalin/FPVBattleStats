type Props = {
  onApply: (from: string, to: string) => void;
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

export function RangeQuickFilters({ onApply }: Props) {
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
    </div>
  );
}
