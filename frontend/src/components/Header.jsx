import { Bot } from "lucide-react";
import { Link } from "react-router-dom";

function Header() {
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

      <div className="system-status">
        <span className="status-dot"></span>
        System Online
      </div>
    </header>
  );
}

export default Header;
