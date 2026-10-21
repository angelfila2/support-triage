import { apiFetch } from "../services/apiFetch";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Inbox, X } from "lucide-react";
import { API_URL } from "../config";

const CATEGORIES = ["password_reset", "billing_question", "shipping_delay", "login_issues", "other"];
const PAGE_SIZE = 25;

function TicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [meta, setMeta] = useState({ total: 0, summary: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [filters, setFilters] = useState({ q: "", category: "", review: "", processing_status: "", urgency: "" });
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const params = new URLSearchParams({ limit: PAGE_SIZE, offset });
        Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
        const response = await apiFetch(`${API_URL}/api/tickets?${params}`, { signal: controller.signal });
        if (!response.ok) throw new Error(`Unable to load tickets (${response.status}). Check your access credential.`);
        const data = await response.json();
        if (!Array.isArray(data.items)) throw new Error("Invalid ticket page.");
        if (!controller.signal.aborted) { setTickets(data.items); setMeta(data); setError(""); }
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
    setLoading(true); setOffset(0); setFilters((old) => ({ ...old, [key]: value }));
  };
  const changePage = (value) => { setLoading(true); setOffset(value); };

  return (
    <div className="tickets-page">
      <div className="tickets-heading"><div><span className="eyebrow">TICKET HISTORY</span><h1>Tickets</h1><p>Search, review and retry support tickets.</p></div>
        <button type="button" disabled={loading} onClick={() => { setLoading(true); setRefresh((old) => old + 1); }}>Refresh</button>
      </div>
      <div className="ticket-summary">
        <SummaryItem label="Matching tickets" value={meta.total} />
        <SummaryItem label="Reviewed" value={meta.summary.reviewed || 0} />
        <SummaryItem label="Correct" value={meta.summary.correct || 0} />
        <SummaryItem label="Pending review" value={meta.summary.pending || 0} />
      </div>
      <div className="ticket-toolbar">
        <input type="search" aria-label="Search tickets" placeholder="Search subject, body or ticket ID" value={filters.q} maxLength={200} onChange={(event) => changeFilter("q", event.target.value)} />
        <select aria-label="Filter by category" value={filters.category} onChange={(event) => changeFilter("category", event.target.value)}>
          <option value="">All categories</option>{CATEGORIES.map((category) => <option key={category} value={category}>{formatCategory(category)}</option>)}
        </select>
        <select aria-label="Filter by review status" value={filters.review} onChange={(event) => changeFilter("review", event.target.value)}>
          <option value="">All reviews</option><option value="pending">Pending</option><option value="correct">Correct</option><option value="incorrect">Incorrect</option>
        </select>
        <select aria-label="Filter by processing status" value={filters.processing_status} onChange={(event) => changeFilter("processing_status", event.target.value)}>
          <option value="">All processing states</option>{["pending", "processing", "completed", "failed"].map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
        <select aria-label="Filter by urgency" value={filters.urgency} onChange={(event) => changeFilter("urgency", event.target.value)}>
          <option value="">All severities</option>{["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"].map((value) => <option key={value}>{value}</option>)}
        </select>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {loading && <p role="status">Loading ticket history...</p>}
      {!loading && !error && tickets.length === 0 && <div className="tickets-empty"><Inbox /><p>No tickets found.</p></div>}
      {!loading && !error && tickets.length > 0 && <div className="tickets-table-card"><div className="tickets-table-wrapper"><table className="tickets-table">
        <thead><tr><th>Ticket</th><th>Request</th><th>Category</th><th>Urgency</th><th>SLA target</th><th>Processing</th><th>Review</th></tr></thead>
        <tbody>{tickets.map((ticket) => <tr key={ticket.id}>
          <td><button type="button" aria-label={`Open ticket ${ticket.id}`} onClick={() => navigate(`/tickets/${ticket.id}`)}>#{ticket.id}</button></td>
          <td><div className="ticket-request"><strong>{ticket.subject}</strong><span>{truncate(ticket.body, 95)}</span></div></td>
          <td>{formatCategory(ticket.category)}</td><td><UrgencyBadge urgency={ticket.urgency} /></td><td>{ticket.sla || "—"}</td>
          <td>{ticket.processing_status}</td><td><ReviewStatus value={ticket.analysis_correct} /></td>
        </tr>)}</tbody>
      </table></div></div>}
      <nav className="ticket-pagination" aria-label="Ticket pages">
        <button type="button" disabled={loading || offset === 0} onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}>Previous page</button>
        <span>{meta.total ? offset + 1 : 0}–{Math.min(offset + tickets.length, meta.total)} of {meta.total}</span>
        <button type="button" disabled={loading || offset + PAGE_SIZE >= meta.total} onClick={() => changePage(offset + PAGE_SIZE)}>Next page</button>
      </nav>
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div className="ticket-summary-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReviewStatus({ value }) {
  let statusClass = "pending";
  let label = "Pending";
  let icon = null;

  if (isTrue(value)) {
    statusClass = "correct";
    label = "Correct";
    icon = <Check size={11} aria-hidden="true" />;
  } else if (isFalse(value)) {
    statusClass = "incorrect";
    label = "Incorrect";
    icon = <X size={11} aria-hidden="true" />;
  }

  return (
    <span className={`review-status ${statusClass}`}>
      {icon}
      {label}
    </span>
  );
}

function UrgencyBadge({ urgency }) {
  const value = String(urgency || "").toLowerCase();

  return (
    <span className={`urgency-badge ${value}`}>
      {value.toUpperCase() || "Unknown"}
    </span>
  );
}

function formatCategory(category) {
  if (!category) return "Unknown";

  return String(category)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function truncate(value, maxLength) { const text = String(value || ""); return text.length > maxLength ? text.slice(0, maxLength) + "…" : text; }

function isTrue(value) { return value === true || value === 1; }
function isFalse(value) { return value === false || value === 0; }

export default TicketsPage;
