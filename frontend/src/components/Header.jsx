import { ChevronRight, Plus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

function Header() {
  const { pathname } = useLocation();
  const page = pathname === "/analytics" ? "Insights" : pathname === "/triage" ? "New ticket" : pathname.startsWith("/tickets/") ? "Ticket details" : "Ticket inbox";
  return <header className="header">
    <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13} /><strong>{page}</strong></div>
    <div className="header-actions">
      <Link to="/triage" className="button primary-button"><Plus size={16} /> New ticket</Link>
    </div>
  </header>;
}
export default Header;
