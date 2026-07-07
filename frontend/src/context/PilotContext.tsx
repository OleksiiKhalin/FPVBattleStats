import { createContext, useContext, useState } from "react";

type PilotContextValue = {
  selectedPilot: string;
  setSelectedPilot: (pilot: string) => void;
};

const PilotContext = createContext<PilotContextValue | null>(null);

export function PilotProvider({ children }: { children: React.ReactNode }) {
  const [selectedPilot, setSelectedPilot] = useState("Select a pilot");

  return <PilotContext.Provider value={{ selectedPilot, setSelectedPilot }}>{children}</PilotContext.Provider>;
}

export function usePilot() {
  const value = useContext(PilotContext);
  if (!value) {
    throw new Error("usePilot must be used inside PilotProvider");
  }
  return value;
}
