import { useEffect, useMemo, useRef, useState } from "react";

import { fetchJson } from "../api/client";
import type { PilotOption } from "../api/types";
import { usePilot } from "../context/PilotContext";
import { useApi } from "../hooks/useApi";

export function PilotSelector() {
  const { selectedPilot, setSelectedPilot, pilotOptions, setPilotOptions } = usePilot();
  const [query, setQuery] = useState(selectedPilot);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const pilots = useApi<PilotOption[]>(() => fetchJson("/analytics/pilots"), []);

  useEffect(() => {
    if (pilots.data) {
      setPilotOptions(pilots.data);
    }
  }, [pilots.data, setPilotOptions]);

  useEffect(() => {
    setQuery(selectedPilot);
  }, [selectedPilot]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return pilotOptions.slice(0, 24);
    }
    return pilotOptions
      .filter((option) => option.pilot.toLowerCase().includes(normalized) || (option.country ?? "").toLowerCase().includes(normalized))
      .slice(0, 24);
  }, [pilotOptions, query]);

  const selectPilot = (pilot: string) => {
    setSelectedPilot(pilot);
    setQuery(pilot);
    setOpen(false);
  };

  return (
    <div className="pilot-selector" ref={rootRef}>
      <span>Pilot viewpoint</span>
      <div className="combo-box">
        <input
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              if (filteredOptions[0]) {
                selectPilot(filteredOptions[0].pilot);
              } else {
                setSelectedPilot(query);
                setOpen(false);
              }
            }
          }}
          placeholder="Search pilot name"
          autoComplete="off"
        />
        <button type="button" className="combo-toggle" onClick={() => setOpen((value) => !value)}>
          v
        </button>
        {open ? (
          <div className="combo-menu">
            {filteredOptions.length === 0 ? <div className="combo-empty">No pilots found</div> : null}
            {filteredOptions.map((option) => (
              <button
                key={option.pilot}
                type="button"
                className={option.pilot === selectedPilot ? "combo-option active" : "combo-option"}
                onClick={() => selectPilot(option.pilot)}
              >
                <span>{option.pilot}</span>
                <small>{option.country ?? "Unknown"}</small>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
