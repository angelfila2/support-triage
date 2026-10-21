import { useState } from "react";
import { ChevronRight, KeyRound, Plus, ShieldCheck } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
function Header() {
  const {
    pathname
  } = useLocation();
  const [token, setToken] = useState("");
  const connected = Boolean(sessionStorage.getItem("supportflow-token"));
  const page = pathname === "/analytics" ? "Insights" : pathname === "/triage" ? "New ticket" : pathname.startsWith("/tickets/") ? "Ticket details" : "Ticket inbox";
  const saveToken = event => {
    event.preventDefault();
    if (token.trim()) sessionStorage.setItem("supportflow-token", token.trim());else sessionStorage.removeItem("supportflow-token");
    window.location.reload();
  };
  return <header className="header">
      <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13} /><strong>{page}</strong></div>
      <div className="header-actions">
        <details className="access-menu">
          <summary aria-label={connected ? "Access configured" : "Connect API"}><KeyRound size={15} /><span>{connected ? "Access configured" : "Connect API"}</span><span className={`connection-dot ${connected ? "configured" : ""}`} /></summary>
          <form onSubmit={saveToken} aria-label="API access" className="access-popover">
            <strong><ShieldCheck size={17} /> Workspace access</strong>
            <p>Enter your API credential to load and manage tickets. It stays in this browser session.</p>
            <label htmlFor="api-token">API access token</label>
            <input id="api-token" type="password" placeholder="Paste your access token" value={token} onChange={event => setToken(event.target.value)} autoComplete="off" />
            <button type="submit" className="primary-button">{connected ? "Replace / clear token" : "Set access token"}</button>
          </form>
        </details>
        <span className="header-divider" />
        <Link to="/triage" className="button primary-button"><Plus size={16} /> New ticket</Link>
      </div>
    </header>;
}
export default Header;
