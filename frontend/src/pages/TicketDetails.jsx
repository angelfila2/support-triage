import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  CircleAlert,
  Clock3,
  Pencil,
  ShieldAlert,
  X,
} from "lucide-react";
import { API_URL } from "../config";

const REVIEW_CATEGORIES = [
  "password_reset",
  "billing_question",
  "shipping_delay",
  "login issues",
  "other",
];

const SEVERITY_OPTIONS = ["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"];

const SLA_MAP = {
  SEV1: "4 hours",
  SEV2: "1 day",
  SEV3: "3 days",
  SEV4: "4 days",
  SEV5: "5 days",
};

function TicketDetails() {
  const { ticketId } = useParams();

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [reviewMode, setReviewMode] = useState(null);
  const [correctedCategory, setCorrectedCategory] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [reviewError, setReviewError] = useState("");

  const [helpdeskMode, setHelpdeskMode] = useState(false);
  const [updatedSeverity, setUpdatedSeverity] = useState("");
  const [responseNotes, setResponseNotes] = useState("");
  const [savingUpdate, setSavingUpdate] = useState(false);
  const [updateError, setUpdateError] = useState("");

  useEffect(() => {
    fetchTicket();
  }, [ticketId]);

  const fetchTicket = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`);

      if (!response.ok) {
        throw new Error(`Unable to load ticket (${response.status})`);
      }

      const tickets = await response.json();

      const foundTicket = tickets.find(
        (item) => String(item.id) === String(ticketId),
      );

      if (!foundTicket) {
        throw new Error(`Ticket ${ticketId} was not found.`);
      }

      setTicket(normalizeTicket(foundTicket));
    } catch (err) {
      console.error(err);

      setError(err.message || "Unable to load ticket.");
    } finally {
      setLoading(false);
    }
  };

  const saveReview = async ({
    analysisCorrect,
    category = null,
    notes = null,
  }) => {
    setSavingReview(true);
    setReviewError("");

    try {
      const response = await fetch(
        `${API_URL}/api/tickets/${encodeURIComponent(ticket.id)}/review`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            analysis_correct: analysisCorrect,
            corrected_category: category,
            review_notes: notes,
          }),
        },
      );

      if (!response.ok) {
        let message = `Unable to save review (${response.status})`;

        try {
          const data = await response.json();

          if (data.detail) {
            message = data.detail;
          }
        } catch {}

        throw new Error(message);
      }

      const updatedTicket = await response.json();

      setTicket(normalizeTicket(updatedTicket));

      setReviewMode(null);
      setCorrectedCategory("");
      setReviewNotes("");
    } catch (err) {
      console.error(err);

      setReviewError(err.message || "Unable to save the review.");
    } finally {
      setSavingReview(false);
    }
  };

  const handleCorrect = () => {
    saveReview({
      analysisCorrect: true,
    });
  };

  const handleIncorrect = () => {
    setReviewMode("incorrect");

    setCorrectedCategory(ticket.category === "other" ? "" : "other");

    setReviewNotes("");
    setReviewError("");
  };

  const handleSaveIncorrect = () => {
    if (!correctedCategory) {
      setReviewError("Please select the correct category.");

      return;
    }

    saveReview({
      analysisCorrect: false,
      category: correctedCategory,
      notes: reviewNotes.trim() || null,
    });
  };

  const handleCancelReview = () => {
    setReviewMode(null);
    setCorrectedCategory("");
    setReviewNotes("");
    setReviewError("");
  };

  const handleOpenHelpdeskUpdate = () => {
    setUpdatedSeverity(String(ticket.urgency || "").toUpperCase());

    setResponseNotes("");
    setUpdateError("");
    setHelpdeskMode(true);
  };

  const handleCancelHelpdeskUpdate = () => {
    setHelpdeskMode(false);
    setUpdatedSeverity("");
    setResponseNotes("");
    setUpdateError("");
  };

  const saveHelpdeskUpdate = async () => {
    if (!updatedSeverity) {
      setUpdateError("Please select a severity.");

      return;
    }

    if (!responseNotes.trim()) {
      setUpdateError("Please enter an update note.");

      return;
    }

    setSavingUpdate(true);
    setUpdateError("");

    try {
      const response = await fetch(
        `${API_URL}/api/tickets/${encodeURIComponent(ticket.id)}/respond`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            responded: true,
            urgency: updatedSeverity,
            response_notes: responseNotes.trim(),
          }),
        },
      );

      if (!response.ok) {
        let message = `Unable to update ticket (${response.status})`;

        try {
          const data = await response.json();

          if (data.detail) {
            message = data.detail;
          }
        } catch {}

        throw new Error(message);
      }

      const updatedTicket = await response.json();

      setTicket(normalizeTicket(updatedTicket));

      setHelpdeskMode(false);
      setUpdatedSeverity("");
      setResponseNotes("");
    } catch (err) {
      console.error(err);

      setUpdateError(err.message || "Unable to save helpdesk update.");
    } finally {
      setSavingUpdate(false);
    }
  };

  if (loading) {
    return (
      <div className="ticket-loading">
        <div className="spinner" />
        <p>Loading ticket...</p>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="ticket-details">
        <Link className="ticket-back-button" to="/tickets">
          <ArrowLeft size={15} />
          All tickets
        </Link>

        <div className="tickets-empty">
          <CircleAlert size={30} />

          <h3>Ticket not found</h3>

          <p>{error || `No ticket exists with ID ${ticketId}.`}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ticket-console">
      <div className="ticket-console-topbar">
        <div>
          <span className="eyebrow">SUPPORT TICKET</span>

          <h1>{ticket.subject || "No subject"}</h1>

          <p>{formatDate(ticket.created_at)}</p>
        </div>

        <div className="ticket-console-actions">
          <ReviewStatus value={ticket.analysis_correct} large />

          <Link className="ticket-back-button" to="/tickets">
            <ArrowLeft size={15} />
            All tickets
          </Link>
        </div>
      </div>

      {isTrue(ticket.is_suspicious) && (
        <div className="suspicious-warning">
          <ShieldAlert size={20} />

          <div>
            <strong>Suspicious content detected</strong>

            <p>
              The safety layer flagged this ticket for potentially malicious
              instructions.
            </p>
          </div>
        </div>
      )}

      <section className="ticket-console-panel ticket-summary-panel">
        <ConsoleSectionTitle>Ticket Summary</ConsoleSectionTitle>

        <div className="ticket-summary-strip">
          <TicketSummaryMetric label="Ticket ID" value={ticket.id || "—"} />

          <TicketSummaryMetric
            label="Category"
            value={formatCategory(ticket.category)}
            variant="success"
          />

          <TicketSummaryMetric
            label="Urgency"
            value={String(ticket.urgency || "").toUpperCase() || "Unknown"}
            variant={getUrgencyVariant(ticket.urgency)}
          />

          <TicketSummaryMetric label="SLA" value={ticket.sla || "—"} />

          <TicketSummaryMetric
            label="Decision"
            value={formatDecision(ticket.decision)}
            variant={ticket.decision === "ESCALATE" ? "warning" : "success"}
          />

          <TicketSummaryMetric
            label="Confidence"
            value={formatConfidence(ticket.confidence)}
          />
        </div>
      </section>

      <div className="ticket-console-grid">
        <div className="ticket-console-main">
          <section className="ticket-console-panel">
            <ConsoleSectionTitle>Customer Request</ConsoleSectionTitle>

            <div className="console-field">
              <span>Subject</span>

              <strong>{ticket.subject || "No subject"}</strong>
            </div>

            <div className="console-field">
              <span>Message</span>

              <div className="console-message-box">{ticket.body || "—"}</div>
            </div>
          </section>

          <section className="ticket-console-panel">
            <ConsoleSectionTitle>Agent Output</ConsoleSectionTitle>

            <div className="console-field">
              <span>AI Reasoning</span>

              <div className="console-message-box">{ticket.reason || "—"}</div>
            </div>

            <div className="console-field">
              <span>Generated Response</span>

              <div className="console-message-box agent-response">
                {ticket.response || "No response generated."}
              </div>
            </div>
          </section>
        </div>

        <aside className="ticket-console-sidebar">
          <section className="ticket-console-panel">
            <ConsoleSectionTitle>Review Actions</ConsoleSectionTitle>

            {isPendingReview(ticket.analysis_correct) &&
              reviewMode !== "incorrect" && (
                <div className="console-review-pending">
                  <p>Was the AI classification correct for this ticket?</p>

                  <div className="review-actions">
                    <button
                      type="button"
                      className="review-correct-button"
                      onClick={handleCorrect}
                      disabled={savingReview}
                    >
                      <Check size={16} />

                      {savingReview ? "Saving..." : "Correct"}
                    </button>

                    <button
                      type="button"
                      className="review-incorrect-button"
                      onClick={handleIncorrect}
                      disabled={savingReview}
                    >
                      <X size={16} />
                      Incorrect
                    </button>
                  </div>
                </div>
              )}

            {isPendingReview(ticket.analysis_correct) &&
              reviewMode === "incorrect" && (
                <div className="review-form">
                  <p>
                    The AI predicted{" "}
                    <strong>{formatCategory(ticket.category)}</strong>. Select
                    the correct classification.
                  </p>

                  <div className="review-form-field">
                    <label htmlFor="corrected-category">Correct category</label>

                    <select
                      id="corrected-category"
                      value={correctedCategory}
                      onChange={(event) => {
                        setCorrectedCategory(event.target.value);

                        setReviewError("");
                      }}
                      disabled={savingReview}
                    >
                      <option value="">Select category</option>

                      {REVIEW_CATEGORIES.map((category) => (
                        <option key={category} value={category}>
                          {formatCategory(category)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="review-form-field">
                    <label htmlFor="review-notes">
                      Review notes
                      <span> Optional</span>
                    </label>

                    <textarea
                      id="review-notes"
                      value={reviewNotes}
                      onChange={(event) => setReviewNotes(event.target.value)}
                      placeholder="Why was the classification incorrect?"
                      rows={4}
                      disabled={savingReview}
                    />
                  </div>

                  {reviewError && (
                    <div className="api-error">
                      <strong>Review failed</strong>

                      <p>{reviewError}</p>
                    </div>
                  )}

                  <div className="review-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={handleCancelReview}
                      disabled={savingReview}
                    >
                      Cancel
                    </button>

                    <button
                      type="button"
                      className="review-incorrect-button"
                      onClick={handleSaveIncorrect}
                      disabled={savingReview || !correctedCategory}
                    >
                      <Check size={16} />

                      {savingReview ? "Saving..." : "Save Review"}
                    </button>
                  </div>
                </div>
              )}

            {isTrue(ticket.analysis_correct) && (
              <div className="console-review-result correct">
                <Check size={19} />

                <div>
                  <strong>Classification verified</strong>

                  <p>The AI classification was confirmed as correct.</p>

                  {ticket.review_notes && (
                    <div className="review-existing-note">
                      {ticket.review_notes}
                    </div>
                  )}
                </div>
              </div>
            )}

            {isFalse(ticket.analysis_correct) && (
              <div className="console-review-result incorrect">
                <CircleAlert size={19} />

                <div>
                  <strong>Classification corrected</strong>

                  <p>
                    AI predicted <b>{formatCategory(ticket.category)}</b>.
                    {ticket.corrected_category && (
                      <>
                        {" "}
                        Corrected to{" "}
                        <b>{formatCategory(ticket.corrected_category)}</b>.
                      </>
                    )}
                  </p>

                  {ticket.review_notes && (
                    <div className="review-existing-note">
                      {ticket.review_notes}
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="ticket-console-panel">
            <ConsoleSectionTitle>Helpdesk Update</ConsoleSectionTitle>

            {!helpdeskMode && (
              <div className="helpdesk-update-summary">
                <div className="console-field">
                  <span>Current Severity</span>

                  <strong>
                    {String(ticket.urgency || "").toUpperCase() || "Unknown"}
                  </strong>
                </div>

                <div className="console-field">
                  <span>Current SLA</span>

                  <strong>{ticket.sla || "—"}</strong>
                </div>

                {ticket.response_datetime && (
                  <div className="console-field">
                    <span>Last Updated</span>

                    <strong>{formatDate(ticket.response_datetime)}</strong>
                  </div>
                )}

                {ticket.response_notes && (
                  <div className="console-field">
                    <span>Update Notes</span>

                    <div className="review-existing-note">
                      {ticket.response_notes}
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleOpenHelpdeskUpdate}
                >
                  <Pencil size={15} />
                  Update Ticket
                </button>
              </div>
            )}

            {helpdeskMode && (
              <div className="review-form">
                <div className="review-form-field">
                  <label htmlFor="updated-severity">Severity</label>

                  <select
                    id="updated-severity"
                    value={updatedSeverity}
                    onChange={(event) => {
                      setUpdatedSeverity(event.target.value);

                      setUpdateError("");
                    }}
                    disabled={savingUpdate}
                  >
                    <option value="">Select severity</option>

                    {SEVERITY_OPTIONS.map((severity) => (
                      <option key={severity} value={severity}>
                        {severity}
                      </option>
                    ))}
                  </select>
                </div>

                {updatedSeverity && (
                  <div className="console-field">
                    <span>Updated SLA</span>

                    <strong>{SLA_MAP[updatedSeverity]}</strong>
                  </div>
                )}

                <div className="review-form-field">
                  <label htmlFor="response-notes">Update Notes</label>

                  <textarea
                    id="response-notes"
                    value={responseNotes}
                    onChange={(event) => {
                      setResponseNotes(event.target.value);

                      setUpdateError("");
                    }}
                    placeholder="Describe the investigation, escalation or severity change..."
                    rows={4}
                    disabled={savingUpdate}
                  />
                </div>

                {updateError && (
                  <div className="api-error">
                    <strong>Update failed</strong>

                    <p>{updateError}</p>
                  </div>
                )}

                <div className="review-actions">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={handleCancelHelpdeskUpdate}
                    disabled={savingUpdate}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    className="review-correct-button"
                    onClick={saveHelpdeskUpdate}
                    disabled={
                      savingUpdate || !updatedSeverity || !responseNotes.trim()
                    }
                  >
                    <Check size={16} />

                    {savingUpdate ? "Saving..." : "Save Update"}
                  </button>
                </div>
              </div>
            )}
          </section>

          <section className="ticket-console-panel">
            <ConsoleSectionTitle>History</ConsoleSectionTitle>

            <div className="ticket-history">
              <HistoryItem
                title="Ticket received"
                description={
                  ticket.created_at
                    ? formatDate(ticket.created_at)
                    : "Ticket submitted"
                }
              />

              <HistoryItem
                title="Triage agent completed"
                description={`${formatCategory(ticket.category)} / ${String(
                  ticket.urgency || "",
                ).toUpperCase()} / ${formatConfidence(ticket.confidence)}`}
              />

              <HistoryItem
                title="Routing decision"
                description={formatDecision(ticket.decision)}
              />

              <HistoryItem
                title={
                  isPendingReview(ticket.analysis_correct)
                    ? "Awaiting human review"
                    : "Human review completed"
                }
                description={
                  isTrue(ticket.analysis_correct)
                    ? "Classification confirmed"
                    : isFalse(ticket.analysis_correct)
                      ? `Corrected to ${formatCategory(
                          ticket.corrected_category,
                        )}`
                      : "Ready for reviewer verification"
                }
                pending={isPendingReview(ticket.analysis_correct)}
              />

              {ticket.response_datetime && (
                <HistoryItem
                  title="Helpdesk update"
                  description={formatDate(ticket.response_datetime)}
                />
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function ConsoleSectionTitle({ children }) {
  return (
    <div className="console-section-title">
      <span className="console-section-dot" />
      <span>{children}</span>
    </div>
  );
}

function TicketSummaryMetric({ label, value, variant = "" }) {
  return (
    <div className={`ticket-summary-metric ${variant}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function HistoryItem({ title, description, pending = false }) {
  return (
    <div className={`ticket-history-item ${pending ? "pending" : ""}`}>
      <div className="history-icon">
        {pending ? <Clock3 size={13} /> : <Check size={13} />}
      </div>

      <div>
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </div>
  );
}

function ReviewStatus({ value, large = false }) {
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
    <span className={`review-status ${statusClass} ${large ? "large" : ""}`}>
      {icon}
      {label}
    </span>
  );
}

function normalizeTicket(ticket) {
  return {
    ...ticket,

    analysis_correct: normalizeOptionalBoolean(ticket.analysis_correct),

    is_suspicious: isTrue(ticket.is_suspicious),

    responded: isTrue(ticket.responded),
  };
}

function normalizeOptionalBoolean(value) {
  if (isTrue(value)) {
    return true;
  }

  if (isFalse(value)) {
    return false;
  }

  return null;
}

function getUrgencyVariant(urgency) {
  const value = String(urgency || "").toUpperCase();

  if (value === "SEV1") {
    return "danger";
  }

  if (value === "SEV2" || value === "SEV3") {
    return "warning";
  }

  if (value === "SEV4" || value === "SEV5") {
    return "success";
  }

  return "";
}

function formatCategory(category) {
  if (!category) {
    return "Unknown";
  }

  return String(category)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDecision(decision) {
  if (!decision) {
    return "Unknown";
  }

  return String(decision)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return "—";
  }

  return `${Math.round(number)}%`;
}

function formatDate(value) {
  if (!value) {
    return "Date unavailable";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
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

export default TicketDetails;
