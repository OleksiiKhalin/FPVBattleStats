import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { PilotProvider } from "./context/PilotContext";
import "./styles/app.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <PilotProvider>
        <App />
      </PilotProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
