import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronRight, Inbox, RefreshCw, Search, X } from "lucide-react";
import { API_URL } from "../config";

function TicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [reviewFilter, setReviewFilter] = useState("all");

  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();

    async function fetchTickets() {
      try {
        const response = await fetch(`${API_URL}/api/tickets`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Unable to load tickets (${response.status}).`);
        }

        const data = await response.json();

        if (
          !Array.isArray(data) ||
          data.some(
            (ticket) =>
              ticket === null ||
              typeof ticket !== "object" ||
              Array.isArray(ticket),
          )
        ) {
          throw new Error("The API returned an invalid ticket list.");
        }

        if (!controller.signal.aborted) {
          setTickets(data);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message || "Unable to connect to the ticket API.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchTickets();

    return () => controller.abort();
  }, [refreshKey]);

  const refreshTickets = () => {
    setLoading(true);
    setError("");
    setRefreshKey((previous) => previous + 1);
  };

  const categories = useMemo(
    () =>
      [
        ...new Set(tickets.map((ticket) => ticket.category).filter(Boolean)),
      ].sort(),
    [tickets],
  );

  const reviewedCount = tickets.filter(
    (ticket) =>
      isTrue(ticket.analysis_correct) || isFalse(ticket.analysis_correct),
  ).length;

  const correctCount = tickets.filter((ticket) =>
    isTrue(ticket.analysis_correct),
  ).length;

  const pendingCount = tickets.filter((ticket) =>
    isPendingReview(ticket.analysis_correct),
  ).length;

  const filteredTickets = useMemo(() => {
    const searchValue = search.trim().toLowerCase();

    return tickets.filter((ticket) => {
      const matchesSearch =
        !searchValue ||
        [ticket.id, ticket.subject, ticket.body, ticket.category].some(
          (value) =>
            String(value ?? "")
              .toLowerCase()
              .includes(searchValue),
        );

      const matchesCategory =
        categoryFilter === "all" || ticket.category === categoryFilter;

      let matchesReview = true;

      if (reviewFilter === "correct") {
        matchesReview = isTrue(ticket.analysis_correct);
      } else if (reviewFilter === "incorrect") {
        matchesReview = isFalse(ticket.analysis_correct);
      } else if (reviewFilter === "pending") {
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
          type="button"
          className="secondary-button"
          onClick={refreshTickets}
          disabled={loading}
        >
          <RefreshCw
            size={14}
            className={loading ? "refresh-spinning" : ""}
            aria-hidden="true"
          />
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
          <Search size={15} aria-hidden="true" />

          <input
            type="search"
            aria-label="Search tickets"
            placeholder="Search ticket, subject or message..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          aria-label="Filter by category"
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
          aria-label="Filter by review status"
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
        <div className="api-error" role="alert">
          <strong>Unable to load tickets</strong>
          <p>{error}</p>
          <p>Check that the backend is running, then click Refresh.</p>
        </div>
      )}

      {loading && (
        <div className="ticket-loading" role="status">
          <div className="spinner" aria-hidden="true" />
          <p>Loading ticket history...</p>
        </div>
      )}

      {!loading && !error && filteredTickets.length === 0 && (
        <div className="tickets-empty">
          <Inbox size={30} aria-hidden="true" />
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
                  <th scope="col">Ticket</th>
                  <th scope="col">Request</th>
                  <th scope="col">Category</th>
                  <th scope="col">Urgency</th>
                  <th scope="col">SLA</th>
                  <th scope="col">Date Received</th>
                  <th scope="col">Expected Response</th>
                  <th scope="col">Review</th>
                  <th scope="col" aria-label="Open ticket" />
                </tr>
              </thead>

              <tbody>
                {filteredTickets.map((ticket) => (
                  <tr
                    key={ticket.id}
                    onClick={() =>
                      navigate(`/tickets/${encodeURIComponent(ticket.id)}`)
                    }
                  >
                    <td className="ticket-id">
                      <button
                        type="button"
                        className="secondary-button"
                        aria-label={`Open ticket ${ticket.id}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          navigate(`/tickets/${encodeURIComponent(ticket.id)}`);
                        }}
                      >
                        {formatTicketId(ticket.id)}
                      </button>
                    </td>

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
                      <span className="ticket-sla">{ticket.sla || "—"}</span>
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
                      <ChevronRight
                        size={15}
                        className="ticket-chevron"
                        aria-hidden="true"
                      />
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

function formatTicketId(value) {
  return value === null || value === undefined || value === ""
    ? "—"
    : String(value);
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getExpectedResponseDate(createdAt, sla) {
  if (!createdAt || !sla) return "—";

  const receivedDate = new Date(createdAt);

  if (Number.isNaN(receivedDate.getTime())) return "—";

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
  if (!value) return "No message content.";

  const text = String(value).replace(/\s+/g, " ").trim();

  return text.length <= length ? text : `${text.slice(0, length)}...`;
}

function isTrue(value) {
  return value === true || value === "true" || value === "True";
}

function isFalse(value) {
  return value === false || value === "false" || value === "False";
}

function isPendingReview(value) {
  return !isTrue(value) && !isFalse(value);
}

export default TicketsPage;
