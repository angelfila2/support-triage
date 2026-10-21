import { Navigate, Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import NewTicketPage from "./pages/NewTicketPage";
import TicketInboxPage from "./pages/TicketInboxPage";
import TicketDetailsPage from "./pages/TicketDetailsPage";
import InsightsPage from "./pages/InsightsPage";
import "./styles/index.css";
function App() {
  return <div className="app">
      <Sidebar />

      <div className="app-shell">
        <Header />

        <main className="main-content">
          <Routes>
            <Route path="/triage" element={<NewTicketPage />} />

            <Route path="/tickets" element={<TicketInboxPage />} />
            <Route path="/" element={<Navigate to="/tickets" replace />} />

            <Route path="/tickets/:ticketId" element={<TicketDetailsPage />} />

            <Route path="/analytics" element={<InsightsPage />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <footer><span>SupportFlow helpdesk</span><span>AI-assisted triage. Human oversight.</span></footer>
      </div>
    </div>;
}
export default App;
