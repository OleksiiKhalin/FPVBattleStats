import { NavLink, Route, Routes } from "react-router-dom";

import { PilotSelector } from "./components/PilotSelector";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { DailyScoreboardPage } from "./pages/DailyScoreboardPage";

export function App() {
  const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? "tab active" : "tab");

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">UA Velocidrone race analytics</p>
          <h1>FPVBattle Stats</h1>
        </div>
        <PilotSelector />
      </header>

      <nav className="tabs">
        <NavLink to="/open" className={navClass}>
          Open Daily
        </NavLink>
        <NavLink to="/whoop" className={navClass}>
          Whoop Daily
        </NavLink>
        <NavLink to="/analytics/open" className={navClass}>
          Open Analytics
        </NavLink>
        <NavLink to="/analytics/whoop" className={navClass}>
          Whoop Analytics
        </NavLink>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<DailyScoreboardPage raceClass="open" />} />
          <Route path="/open" element={<DailyScoreboardPage raceClass="open" />} />
          <Route path="/whoop" element={<DailyScoreboardPage raceClass="whoop" />} />
          <Route path="/analytics/:raceClass" element={<AnalyticsPage />} />
        </Routes>
      </main>
    </div>
  );
}
