import { ArrowUpRight, BarChart3, Inbox, Plus, ShieldCheck, Sparkles } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
function Sidebar() {
  return <aside className="sidebar">
      <Link to="/tickets" className="sidebar-logo" aria-label="SupportFlow home">
        <span className="logo-mark"><img src="/support-corgi.png" alt="Corgi wearing a support headset" width="40" height="40" /></span>
        <span>supportflow<span className="brand-period">.</span></span>
      </Link>
      <div className="workspace-switch"><span className="workspace-avatar">S</span><div><strong>Support workspace</strong><small>IT service desk</small></div></div>
      <span className="nav-caption">WORKSPACE</span>
      <nav className="sidebar-nav" aria-label="Main navigation">
        <NavLink aria-label="Ticket inbox" title="Ticket inbox" to="/tickets" className={({
        isActive
      }) => `sidebar-button ${isActive ? "active" : ""}`}><Inbox size={18} /><span>Ticket inbox</span></NavLink>
        <NavLink aria-label="New ticket" title="New ticket" to="/triage" className={({
        isActive
      }) => `sidebar-button ${isActive ? "active" : ""}`}><Plus size={18} /><span>New ticket</span></NavLink>
        <NavLink aria-label="Insights" title="Insights" to="/analytics" className={({
        isActive
      }) => `sidebar-button ${isActive ? "active" : ""}`}><BarChart3 size={18} /><span>Insights</span></NavLink>
      </nav>
      <div className="sidebar-bottom">
        <div className="assistant-note"><span className="assistant-note-icon"><Sparkles size={17} /> AI, with a human touch</span><p>Routine requests, handled faster. Critical issues, escalated.</p><Link to="/triage">Try AI triage <ArrowUpRight size={14} /></Link></div>
        <div className="workspace-footer"><ShieldCheck size={17} /><div><strong>Human oversight</strong><small>Review every AI decision</small></div></div>
      </div>
    </aside>;
}
export default Sidebar;
