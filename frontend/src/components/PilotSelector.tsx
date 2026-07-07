import { ChangeEvent } from "react";

import { usePilot } from "../context/PilotContext";

export function PilotSelector() {
  const { selectedPilot, setSelectedPilot } = usePilot();

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedPilot(event.target.value);
  };

  return (
    <label className="pilot-selector">
      <span>Pilot viewpoint</span>
      <input value={selectedPilot} onChange={handleChange} placeholder="Enter pilot name" />
    </label>
  );
}
