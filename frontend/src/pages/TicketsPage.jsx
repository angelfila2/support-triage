import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronRight, Inbox, RefreshCw, Search, X } from "lucide-react";
import { API_URL } from "../config";

function TicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [reviewFilter, setReviewFilter] = useState("all");

  const navigate = useNavigate();

  const fetchTickets = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`);

      if (!response.ok) {
        throw new Error(`Unable to load tickets (${response.status})`);
      }

      const data = await response.json();

      setTickets(data);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to connect to the ticket API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const categories = useMemo(() => {
    return [
      ...new Set(tickets.map((ticket) => ticket.category).filter(Boolean)),
    ].sort();
  }, [tickets]);

  const reviewedCount = useMemo(() => {
    return tickets.filter(
      (ticket) =>
        isTrue(ticket.analysis_correct) || isFalse(ticket.analysis_correct),
    ).length;
  }, [tickets]);

  const correctCount = useMemo(() => {
    return tickets.filter((ticket) => isTrue(ticket.analysis_correct)).length;
  }, [tickets]);

  const pendingCount = useMemo(() => {
    return tickets.filter((ticket) => isPendingReview(ticket.analysis_correct))
      .length;
  }, [tickets]);

  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      const searchValue = search.trim().toLowerCase();

      const matchesSearch =
        !searchValue ||
        String(ticket.id || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(ticket.subject || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(ticket.body || "")
          .toLowerCase()
          .includes(searchValue) ||
        String(ticket.category || "")
          .toLowerCase()
          .includes(searchValue);

      const matchesCategory =
        categoryFilter === "all" || ticket.category === categoryFilter;

      let matchesReview = true;

      if (reviewFilter === "correct") {
        matchesReview = isTrue(ticket.analysis_correct);
      }

      if (reviewFilter === "incorrect") {
        matchesReview = isFalse(ticket.analysis_correct);
      }

      if (reviewFilter === "pending") {
        matchesReview = isPendingReview(ticket.analysis_correct);
      }

      return matchesSearch && matchesCategory && matchesReview;
    });
  }, [tickets, search, categoryFilter, reviewFilter]);

  return (
    <div className="tickets-page">
      <div className="tickets-heading">
        <div>
          <span className="eyebrow">TICKET HISTORY</span>

          <h1>Tickets</h1>

          <p>
            Review previously analysed support tickets and verify the AI
            classification.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={fetchTickets}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "refresh-spinning" : ""} />
          Refresh
        </button>
      </div>

      <div className="ticket-summary">
        <SummaryItem label="Tickets" value={tickets.length} />

        <SummaryItem label="Reviewed" value={reviewedCount} />

        <SummaryItem label="Correct" value={correctCount} />

        <SummaryItem label="Pending" value={pendingCount} />
      </div>

      <div className="ticket-toolbar">
        <div className="ticket-search">
          <Search size={15} />

          <input
            type="text"
            placeholder="Search ticket, subject or message..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          value={categoryFilter}
          onChange={(event) => setCategoryFilter(event.target.value)}
        >
          <option value="all">All categories</option>

          {categories.map((category) => (
            <option key={category} value={category}>
              {formatCategory(category)}
            </option>
          ))}
        </select>

        <select
          value={reviewFilter}
          onChange={(event) => setReviewFilter(event.target.value)}
        >
          <option value="all">All reviews</option>

          <option value="pending">Pending</option>

          <option value="correct">Correct</option>

          <option value="incorrect">Incorrect</option>
        </select>
      </div>

      {error && (
        <div className="api-error">
          <strong>Unable to load tickets</strong>

          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="ticket-loading">
          <div className="spinner" />

          <p>Loading ticket history...</p>
        </div>
      )}

      {!loading && !error && filteredTickets.length === 0 && (
        <div className="tickets-empty">
          <Inbox size={30} />

          <h3>No tickets found</h3>

          <p>Analyse a support email or change your filters.</p>
        </div>
      )}

      {!loading && !error && filteredTickets.length > 0 && (
        <div className="tickets-table-card">
          <div className="tickets-table-wrapper">
            <table className="tickets-table">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Request</th>
                  <th>Category</th>
                  <th>Urgency</th>
                  <th>SLA</th>
                  <th>Date Received</th>
                  <th>Expected Response</th>
                  <th>Review</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                {filteredTickets.map((ticket, index) => (
                  <tr
                    key={ticket.id || `ticket-${index}`}
                    onClick={() =>
                      navigate(`/tickets/${encodeURIComponent(ticket.id)}`)
                    }
                  >
                    <td className="ticket-id">{formatTicketId(ticket.id)}</td>

                    <td>
                      <div className="ticket-request">
                        <strong>{ticket.subject || "No subject"}</strong>

                        <span>{truncate(ticket.body, 95)}</span>
                      </div>
                    </td>

                    <td>
                      <span className="category-badge">
                        {formatCategory(ticket.category)}
                      </span>
                    </td>

                    <td>
                      <UrgencyBadge urgency={ticket.urgency} />
                    </td>

                    <td>
                      <span className="ticket-sla">{ticket.sla}</span>
                    </td>

                    <td>
                      <span className="ticket-date">
                        {formatDate(ticket.created_at)}
                      </span>
                    </td>

                    <td>
                      <span className="ticket-date">
                        {getExpectedResponseDate(ticket.created_at, ticket.sla)}
                      </span>
                    </td>

                    <td>
                      <ReviewStatus value={ticket.analysis_correct} />
                    </td>

                    <td>
                      <ChevronRight size={15} className="ticket-chevron" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
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
    icon = <Check size={11} />;
  }

  if (isFalse(value)) {
    statusClass = "incorrect";
    label = "Incorrect";
    icon = <X size={11} />;
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
  if (!category) {
    return "Unknown";
  }

  return String(category)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTicketId(value) {
  return value ? String(value) : "—";
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getExpectedResponseDate(createdAt, sla) {
  if (!createdAt || !sla) {
    return "—";
  }

  const receivedDate = new Date(createdAt);

  if (Number.isNaN(receivedDate.getTime())) {
    return "—";
  }

  const slaValue = String(sla).trim().toLowerCase();

  let expectedDate;

  if (slaValue === "4 hours") {
    expectedDate = addBusinessHours(receivedDate, 4);
  } else if (slaValue === "1 day") {
    expectedDate = addBusinessDays(receivedDate, 1);
  } else if (slaValue === "3 days") {
    expectedDate = addBusinessDays(receivedDate, 3);
  } else if (slaValue === "4 days") {
    expectedDate = addBusinessDays(receivedDate, 4);
  } else if (slaValue === "5 days") {
    expectedDate = addBusinessDays(receivedDate, 5);
  } else {
    return "—";
  }

  return formatDate(expectedDate);
}

function addBusinessDays(startDate, days) {
  const result = new Date(startDate);

  let businessDaysAdded = 0;

  while (businessDaysAdded < days) {
    result.setDate(result.getDate() + 1);

    if (isBusinessDay(result)) {
      businessDaysAdded += 1;
    }
  }

  return result;
}

function addBusinessHours(startDate, hours) {
  const result = new Date(startDate);

  let hoursRemaining = hours;

  while (hoursRemaining > 0) {
    result.setHours(result.getHours() + 1);

    if (isBusinessDay(result)) {
      hoursRemaining -= 1;
    }
  }

  return result;
}

function isBusinessDay(date) {
  const day = date.getDay();

  return day !== 0 && day !== 6;
}

function truncate(value, length) {
  if (!value) {
    return "No message content.";
  }

  const text = String(value).replace(/\s+/g, " ").trim();

  if (text.length <= length) {
    return text;
  }

  return `${text.slice(0, length)}...`;
}

function isTrue(value) {
  return value === true || value === "true" || value === "True";
}

function isFalse(value) {
  return value === false || value === "false" || value === "False";
}

function isPendingReview(value) {
  return (
    value === null ||
    value === undefined ||
    value === "" ||
    (!isTrue(value) && !isFalse(value))
  );
}

export default TicketsPage;
