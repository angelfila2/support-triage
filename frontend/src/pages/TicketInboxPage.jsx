import { apiFetch } from "../services/api";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, CheckCheck, ChevronLeft, ChevronRight, Clock3, CornerUpRight, Inbox, Plus, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Sparkles, UserRoundCheck, X } from "lucide-react";
import { Link } from "react-router-dom";
import { API_URL } from "../config";
const CATEGORIES = ["password_reset", "billing_question", "shipping_delay", "login_issues", "other"];
const PAGE_SIZE = 25;
function TicketInboxPage() {
  const [tickets, setTickets] = useState([]);
  const [meta, setMeta] = useState({
    total: 0,
    summary: {}
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [filters, setFilters] = useState({
    q: "",
    category: "",
    review: "",
    processing_status: "",
    urgency: ""
  });
  const navigate = useNavigate();
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const params = new URLSearchParams({
          limit: PAGE_SIZE,
          offset
        });
        Object.entries(filters).forEach(([key, value]) => {
          if (value) params.set(key, value);
        });
        const response = await apiFetch(`${API_URL}/api/tickets?${params}`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error(`Unable to load tickets (${response.status}). Check that the backend is running, then restart both servers if you changed backend/.env.`);
        const data = await response.json();
        if (!Array.isArray(data.items)) throw new Error("Invalid ticket page.");
        if (!controller.signal.aborted) {
          setTickets(data.items);
          setMeta(data);
          setError("");
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    load();
    return () => controller.abort();
  }, [filters, offset, refresh]);
  const changeFilter = (key, value) => {
    setLoading(true);
    setOffset(0);
    setFilters(old => ({
      ...old,
      [key]: value
    }));
  };
  const changePage = value => {
    setLoading(true);
    setOffset(value);
  };
  const tabs = [{
    label: "All tickets",
    active: !filters.review && !filters.processing_status,
    values: {
      review: "",
      processing_status: ""
    }
  }, {
    label: "Awaiting review",
    active: filters.review === "pending",
    values: {
      review: "pending",
      processing_status: ""
    }
  }, {
    label: "Needs retry",
    active: filters.processing_status === "failed",
    values: {
      review: "",
      processing_status: "failed"
    }
  }];
  return <div className="tickets-page">
      <div className="tickets-heading"><div><span className="eyebrow">SERVICE DESK</span><h1>Ticket inbox<span className="heading-count">{meta.total}</span></h1><p>A clear view of every request. A faster path to resolution.</p></div>
        <button className="secondary-button" type="button" disabled={loading} onClick={() => {
        setLoading(true);
        setRefresh(old => old + 1);
      }}><RefreshCw size={14} className={loading ? "spinning" : ""} /> Refresh</button>
      </div>
      <div className="ticket-summary">
        <SummaryItem label="Matching tickets" value={meta.total} icon={<Inbox size={18} />} tone="blue" />
        <SummaryItem label="Reviewed by a human" value={meta.summary.reviewed || 0} icon={<UserRoundCheck size={18} />} tone="purple" />
        <SummaryItem label="AI decisions approved" value={meta.summary.correct || 0} icon={<CheckCheck size={18} />} tone="green" />
        <SummaryItem label="Not yet reviewed" value={meta.summary.pending || 0} icon={<Clock3 size={18} />} tone="amber" />
      </div>
      <section className="queue-panel" aria-label="Ticket queue">
        <div className="queue-tabs" aria-label="Queue views">{tabs.map(tab => <button type="button" key={tab.label} aria-pressed={tab.active} onClick={() => {
          setLoading(true);
          setOffset(0);
          setFilters(old => ({
            ...old,
            ...tab.values
          }));
        }}>{tab.label}</button>)}<span><Sparkles size={13} /> AI-assisted triage</span></div>
        <div className="ticket-toolbar">
          <div className="queue-search"><Search size={16} /><input type="search" aria-label="Search tickets" placeholder="Search tickets..." value={filters.q} maxLength={200} onChange={event => changeFilter("q", event.target.value)} /></div>
          <span className="filter-label"><SlidersHorizontal size={14} /> Filter</span>
          <select aria-label="Filter by category" value={filters.category} onChange={event => changeFilter("category", event.target.value)}>
            <option value="">All categories</option>{CATEGORIES.map(category => <option key={category} value={category}>{formatCategory(category)}</option>)}
          </select>
          <select aria-label="Filter by processing status" value={filters.processing_status} onChange={event => changeFilter("processing_status", event.target.value)}>
            <option value="">All statuses</option>{["pending", "processing", "completed", "failed"].map(value => <option key={value} value={value}>{value === "completed" ? "Triaged" : value.charAt(0).toUpperCase() + value.slice(1)}</option>)}
          </select>
          <select aria-label="Filter by urgency" value={filters.urgency} onChange={event => changeFilter("urgency", event.target.value)}>
            <option value="">All priorities</option>{["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"].map(value => <option key={value}>{value}</option>)}
          </select>
          <select aria-label="Filter by review status" value={filters.review} onChange={event => changeFilter("review", event.target.value)}>
            <option value="">All reviews</option><option value="pending">Not reviewed</option><option value="correct">Approved</option><option value="incorrect">Corrected</option>
          </select>
        </div>
        {error && <div className="api-error" role="alert"><strong>We couldn’t load your inbox</strong><p>{error}</p><span>Start the backend and frontend from this project folder.</span></div>}
        {loading && <div className="queue-loading" role="status"><span className="spinner" />Loading ticket inbox...</div>}
        {!loading && !error && tickets.length === 0 && <div className="tickets-empty"><span className="empty-icon"><Inbox size={28} /></span><h2>A little breathing room.</h2><p>{Object.values(filters).some(Boolean) ? "No tickets match these filters. Try a different search." : "Your inbox is ready. Create a ticket to see AI triage in action."}</p><Link to="/triage" className="button primary-button"><Plus size={15} /> Create a ticket</Link></div>}
        {!loading && !error && tickets.length > 0 && <div className="tickets-table-wrapper"><table className="tickets-table">
          <thead><tr><th scope="col">Ticket / subject</th><th scope="col">Priority</th><th scope="col">Status</th><th scope="col">AI routing</th><th scope="col">Review</th><th scope="col">Created</th><th scope="col">Deadline</th><th scope="col"><span className="sr-only">Open ticket</span></th></tr></thead>
          <tbody>{tickets.map(ticket => <tr key={ticket.id}>
            <td><div className="ticket-request"><div><span className="ticket-number">#{ticket.id}</span><span className="category-label">{formatCategory(ticket.category)}</span></div><Link to={`/tickets/${ticket.id}`} className="ticket-subject">{ticket.subject || "Untitled request"}</Link><span className="ticket-excerpt">{truncate(ticket.body, 75)}</span></div></td>
            <td><UrgencyBadge urgency={ticket.urgency} /><small className="sla-caption">{ticket.sla ? `${ticket.sla} target` : "Not assigned"}</small></td>
            <td><span className={`process-badge ${ticket.processing_status}`}><i />{{
                    completed: "Triaged",
                    processing: "Processing",
                    pending: "Pending",
                    failed: "Failed"
                  }[ticket.processing_status] || "Unknown"}</span></td>
            <td>{ticket.decision ? <span className={`routing-label ${ticket.decision === "AUTO_REPLY" ? "auto" : "escalated"}`}>{ticket.decision === "AUTO_REPLY" ? <Sparkles size={13} /> : <CornerUpRight size={13} />}{ticket.decision === "AUTO_REPLY" ? "Auto reply" : "Escalated"}</span> : <span className="muted">Awaiting triage</span>}</td>
            <td><ReviewStatus value={ticket.analysis_correct} /></td>
            <td className="date-cell">{formatDate(ticket.created_at)}</td>
            <td className="deadline-cell">{formatDeadline(ticket)}</td>
            <td><button type="button" className="ticket-open" aria-label={`Open ticket ${ticket.id}`} onClick={() => navigate(`/tickets/${ticket.id}`)}><ChevronRight size={16} /></button></td>
          </tr>)}</tbody>
        </table></div>}
        <nav className="ticket-pagination" aria-label="Ticket pages">
          <span>{loading ? "Loading..." : `Showing ${meta.total ? offset + 1 : 0}–${Math.min(offset + tickets.length, meta.total)} of ${meta.total} tickets`}</span>
          <div><button type="button" disabled={loading || offset === 0} onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}><ChevronLeft size={14} /> Previous</button><button type="button" disabled={loading || offset + PAGE_SIZE >= meta.total} onClick={() => changePage(offset + PAGE_SIZE)}>Next <ChevronRight size={14} /></button></div>
        </nav>
      </section>
      <p className="queue-footnote"><ShieldCheck size={13} /> Critical incidents always reach a human. AI replies stay grounded in your knowledge base.</p>
    </div>;
}
function SummaryItem({
  label,
  value,
  icon,
  tone
}) {
  return <div className="ticket-summary-item">
      <div><span>{label}</span><strong>{value}</strong></div><span className={`summary-icon ${tone}`}>{icon}</span>
    </div>;
}
function ReviewStatus({
  value
}) {
  let statusClass = "pending";
  let label = "Not reviewed";
  let icon = null;
  if (isTrue(value)) {
    statusClass = "correct";
    label = "Approved";
    icon = <Check size={11} aria-hidden="true" />;
  } else if (isFalse(value)) {
    statusClass = "incorrect";
    label = "Corrected";
    icon = <X size={11} aria-hidden="true" />;
  }
  return <span className={`review-status ${statusClass}`}>
      {icon}
      {label}
    </span>;
}
function UrgencyBadge({
  urgency
}) {
  const value = String(urgency || "").toLowerCase();
  return <span className={`urgency-badge ${value}`}>
      <i />{{
      sev1: "Critical",
      sev2: "High",
      sev3: "Medium",
      sev4: "Low",
      sev5: "Info"
    }[value] || "Unassigned"}<small>{value.toUpperCase()}</small>
    </span>;
}
function formatCategory(category) {
  if (!category) return "Unassigned";
  return String(category).replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}
function truncate(value, maxLength) {
  const text = String(value || "");
  return text.length > maxLength ? text.slice(0, maxLength) + "…" : text;
}
function isTrue(value) {
  return value === true || value === 1;
}
function isFalse(value) {
  return value === false || value === 0;
}
function formatDate(value) {
  if (!value || Number.isNaN(new Date(value).getTime())) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric"
  });
}
export default TicketInboxPage;

function formatDeadline(ticket) {
  const hours = { SEV1: 4, SEV2: 24, SEV3: 72, SEV4: 96, SEV5: 120 }[ticket.urgency];
  const created = new Date(ticket.created_at);
  if (!hours || Number.isNaN(created.getTime())) return "Not assigned";
  return new Date(created.getTime() + hours * 3600000).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit"
  });
}
