import { useEffect, useMemo, useRef, useState } from "react";

import { fetchJson } from "../api/client";
import type { PilotOption } from "../api/types";
import { useApi } from "../hooks/useApi";

type Props = {
  primaryPilot: string;
  raceClass: string;
  value: string;
  onChange: (pilot: string) => void;
};

const RECENT_PILOTS_KEY = "fpvbattle-recent-comparison-pilots";

function readRecentPilots() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_PILOTS_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

export function PilotComparisonPicker({ primaryPilot, raceClass, value, onChange }: Props) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [recentPilots, setRecentPilots] = useState<string[]>(readRecentPilots);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const pilots = useApi<PilotOption[]>(() => fetchJson(`/analytics/pilots?race_class=${raceClass}`), [raceClass]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const firstPilot = pilots.data?.find((pilot) => pilot.pilot !== primaryPilot)?.pilot ?? "";
    const isValid = value && value !== primaryPilot && pilots.data?.some((pilot) => pilot.pilot === value);
    if (!isValid && firstPilot && firstPilot !== value) onChange(firstPilot);
  }, [onChange, pilots.data, primaryPilot, raceClass, value]);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  const options = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (pilots.data ?? [])
      .filter((pilot) => pilot.pilot !== primaryPilot)
      .filter((pilot) => !normalized || pilot.pilot.toLowerCase().includes(normalized) || (pilot.country ?? "").toLowerCase().includes(normalized))
      .slice(0, 24);
  }, [pilots.data, primaryPilot, query]);

  const selectOpponent = (pilot: string) => {
    onChange(pilot);
    setQuery(pilot);
    setOpen(false);
    const nextRecent = [pilot, ...recentPilots.filter((recentPilot) => recentPilot !== pilot && recentPilot !== primaryPilot)].slice(0, 5);
    setRecentPilots(nextRecent);
    localStorage.setItem(RECENT_PILOTS_KEY, JSON.stringify(nextRecent));
    sessionStorage.setItem("fpvbattle-comparison-opponent", pilot);
  };

  const availableRecentPilots = recentPilots.filter((pilot) => pilot !== primaryPilot);

  return (
    <div className="comparison-controls">
      <div className="comparison-picker" ref={rootRef}>
        <label className="field"><span>Compare with</span>
          <div className="combo-box">
            <input value={query} onFocus={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onKeyDown={(event) => { if (event.key === "Enter" && options[0]) { event.preventDefault(); selectOpponent(options[0].pilot); } }} placeholder="Search pilot name" autoComplete="off" />
            <button type="button" className="combo-toggle" onClick={() => setOpen((current) => !current)} aria-label="Toggle pilot list">v</button>
            {open ? <div className="combo-menu">{options.length === 0 ? <div className="combo-empty">No pilots found</div> : options.map((pilot) => <button key={pilot.pilot} type="button" className={pilot.pilot === value ? "combo-option active" : "combo-option"} onClick={() => selectOpponent(pilot.pilot)}><span>{pilot.pilot}</span><small>{pilot.country ?? "Unknown"}</small></button>)}</div> : null}
          </div>
        </label>
      </div>
      {availableRecentPilots.length ? <div className="quick-filters recent-pilots"><span>Recent pilots</span>{availableRecentPilots.map((pilot) => <button className={pilot === value ? "chip active" : "chip"} type="button" key={pilot} onClick={() => selectOpponent(pilot)}>{pilot}</button>)}</div> : null}
    </div>
  );
}
