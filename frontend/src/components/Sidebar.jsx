import { BarChart3, Bot, Mail, Tickets } from "lucide-react";

import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Bot size={22} />
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `sidebar-button ${isActive ? "active" : ""}`
          }
          title="Triage"
        >
          <Mail size={19} />
        </NavLink>

        <NavLink
          to="/tickets"
          className={({ isActive }) =>
            `sidebar-button ${isActive ? "active" : ""}`
          }
          title="Tickets"
        >
          <Tickets size={19} />
        </NavLink>

        <NavLink
          to="/analytics"
          className={({ isActive }) =>
            `sidebar-button ${isActive ? "active" : ""}`
          }
          title="Analytics"
        >
          <BarChart3 size={19} />
        </NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;
