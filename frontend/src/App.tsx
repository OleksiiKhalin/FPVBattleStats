import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { PilotSelector } from "./components/PilotSelector";
import { usePilot } from "./context/PilotContext";
import { DailyScoreboardPage } from "./pages/DailyScoreboardPage";
import { GeneralStatsPage } from "./pages/GeneralStatsPage";
import { PilotStatsPage } from "./pages/PilotStatsPage";

const TODAY = new Date().toISOString().slice(0, 10);

export function App() {
  const { selectedPilot } = usePilot();
  const location = useLocation();
  const navigate = useNavigate();
  const compareReturn = new URLSearchParams(location.search).get("compare_return") ?? (location.state as { compareReturn?: string } | null)?.compareReturn;
  const [selectedDailyDate, setSelectedDailyDate] = useState(TODAY);
  useEffect(() => {
    const date = new URLSearchParams(location.search).get("date");
    if (date) setSelectedDailyDate(date);
  }, [location.search]);

  const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab");
  const pilotSearch = `?pilot=${encodeURIComponent(selectedPilot)}`;
  const isDailyPage = location.pathname === "/" || location.pathname === "/open" || location.pathname === "/whoop";

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Tight daily leaderboard and historical race analytics</p>
          <h1>FPVBattle Stats</h1>
        </div>
        <div className="topbar-controls">
          {isDailyPage && compareReturn ? <button type="button" className="chip" onClick={() => navigate(compareReturn)}>Back to comparison</button> : null}
          {isDailyPage ? (
            <label className="date-selector">
              <span>Daily date</span>
              <div className="date-selector-row">
                <input type="date" value={selectedDailyDate} onChange={(event) => setSelectedDailyDate(event.target.value)} />
                {selectedDailyDate !== TODAY ? (
                  <button type="button" className="chip" onClick={() => setSelectedDailyDate(TODAY)}>
                    Back to today
                  </button>
                ) : null}
              </div>
            </label>
          ) : null}
          <PilotSelector />
        </div>
      </header>

      <nav className="tabs">
        <NavLink to={`/open${pilotSearch}`} className={navClass}>
          Open Daily
        </NavLink>
        <NavLink to={`/whoop${pilotSearch}`} className={navClass}>
          Whoop Daily
        </NavLink>
        <NavLink to={`/pilot-stats${pilotSearch}`} className={navClass}>
          Pilot Stats
        </NavLink>
        <NavLink to={`/general-stats${pilotSearch}`} className={navClass}>
          General Stats
        </NavLink>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<DailyScoreboardPage raceClass="open" selectedDate={selectedDailyDate} />} />
          <Route path="/open" element={<DailyScoreboardPage raceClass="open" selectedDate={selectedDailyDate} />} />
          <Route path="/whoop" element={<DailyScoreboardPage raceClass="whoop" selectedDate={selectedDailyDate} />} />
          <Route path="/pilot-stats" element={<PilotStatsPage />} />
          <Route path="/general-stats" element={<GeneralStatsPage />} />
        </Routes>
      </main>
    </div>
  );
}
