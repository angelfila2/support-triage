import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import Header from "./components/Header";
import Sidebar from "./components/Sidebar";

import TriagePage from "./pages/TriagePage";
import TicketsPage from "./pages/TicketsPage";
import TicketDetails from "./pages/TicketDetails";
import AnalyticsPage from "./pages/AnalyticsPage";

import "./App.css";

function App() {
  const [triageHistory, setTriageHistory] = useState([]);

  const handleTriageComplete = (result) => {
    setTriageHistory((previous) => [...previous, result]);
  };

  return (
    <div className="app">
      <Sidebar />

      <div className="app-shell">
        <Header />

        <main className="main-content">
          <Routes>
            <Route
              path="/"
              element={<TriagePage onTriageComplete={handleTriageComplete} />}
            />

            <Route path="/tickets" element={<TicketsPage />} />

            <Route path="/tickets/:ticketId" element={<TicketDetails />} />

            <Route
              path="/analytics"
              element={<AnalyticsPage history={triageHistory} />}
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <footer>SupportFlow · AI Support Ticket Triage</footer>
      </div>
    </div>
  );
}

export default App;
