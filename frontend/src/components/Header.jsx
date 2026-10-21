import { useState } from "react";
import { Bot } from "lucide-react";
import { Link } from "react-router-dom";

function Header() {
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(Boolean(sessionStorage.getItem("supportflow-token")));
  const saveToken = (event) => {
    event.preventDefault();
    if (token.trim()) sessionStorage.setItem("supportflow-token", token.trim());
    else sessionStorage.removeItem("supportflow-token");
    setToken("");
    setConnected(Boolean(sessionStorage.getItem("supportflow-token")));
    window.location.reload();
  };
  return (
    <header className="header">
      <Link to="/" className="brand">
        <div className="brand-icon">
          <Bot size={24} />
        </div>

        <div>
          <h1>SupportFlow</h1>
          <p>AI Support Ticket Triage</p>
        </div>
      </Link>

      <form onSubmit={saveToken} aria-label="API access">
        <input type="password" aria-label="API access token" placeholder="API access token"
          value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" />
        <button type="submit">{connected ? "Replace / clear token" : "Set access token"}</button>
      </form>
      <div className="system-status">
        <span className="status-dot"></span>
        {connected ? "Credential set" : "No credential"}
      </div>
    </header>
  );
}

export default Header;
