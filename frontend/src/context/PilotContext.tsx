import { createContext, useContext, useState } from "react";

import type { PilotOption } from "../api/types";

type PilotContextValue = {
  selectedPilot: string;
  setSelectedPilot: (pilot: string) => void;
  pilotOptions: PilotOption[];
  setPilotOptions: (pilots: PilotOption[]) => void;
};

const PilotContext = createContext<PilotContextValue | null>(null);

export function PilotProvider({ children }: { children: React.ReactNode }) {
  const [selectedPilot, setSelectedPilot] = useState("MGescapades");
  const [pilotOptions, setPilotOptions] = useState<PilotOption[]>([]);

  return (
    <PilotContext.Provider value={{ selectedPilot, setSelectedPilot, pilotOptions, setPilotOptions }}>
      {children}
    </PilotContext.Provider>
  );
}

export function usePilot() {
  const value = useContext(PilotContext);
  if (!value) {
    throw new Error("usePilot must be used inside PilotProvider");
  }
  return value;
}
