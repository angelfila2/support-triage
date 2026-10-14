import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Clock3, Pencil, ShieldAlert, X } from "lucide-react";
import { API_URL } from "../config";

const REVIEW_CATEGORIES = [
  "password_reset",
  "billing_question",
  "shipping_delay",
  "login_issues",
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

  // Reset page and form state when navigating to a different ticket.
  return <TicketDetailsContent key={ticketId} ticketId={ticketId} />;
}

function TicketDetailsContent({ ticketId }) {
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
    const controller = new AbortController();

    async function fetchTicket() {
      try {
        const response = await fetch(
          `${API_URL}/api/tickets/${encodeURIComponent(ticketId)}`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error(
            response.status === 404
              ? "This ticket does not exist."
              : `Unable to load ticket (${response.status}).`,
          );
        }

        const data = normalizeTicket(await response.json());

        if (!controller.signal.aborted) {
          setTicket(data);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message || "Unable to load ticket.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchTicket();

    return () => controller.abort();
  }, [ticketId]);

  const saveReview = async ({
    analysisCorrect,
    category = null,
    notes = null,
  }) => {
    if (savingReview) return;

    if (!analysisCorrect && !REVIEW_CATEGORIES.includes(category)) {
      setReviewError("Select the correct category before saving.");
      return;
    }

    setSavingReview(true);
    setReviewError("");

    try {
      const response = await fetch(
        `${API_URL}/api/tickets/${encodeURIComponent(ticket.id)}/review`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            analysis_correct: analysisCorrect,
            corrected_category: analysisCorrect ? null : category,
            review_notes: notes?.trim() || null,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(response, "Unable to save review."),
        );
      }

      setTicket(normalizeTicket(await response.json()));
      setReviewMode(null);
      setCorrectedCategory("");
      setReviewNotes("");
    } catch (err) {
      setReviewError(err.message || "Unable to save review.");
    } finally {
      setSavingReview(false);
    }
  };

  const saveHelpdeskUpdate = async () => {
    if (savingUpdate) return;

    if (!SEVERITY_OPTIONS.includes(updatedSeverity)) {
      setUpdateError("Select a valid urgency level.");
      return;
    }

    setSavingUpdate(true);
    setUpdateError("");

    try {
      const response = await fetch(
        `${API_URL}/api/tickets/${encodeURIComponent(ticket.id)}/respond`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            responded: true,
            urgency: updatedSeverity,
            response_notes: responseNotes.trim() || null,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(response, "Unable to update ticket."),
        );
      }

      setTicket(normalizeTicket(await response.json()));
      setHelpdeskMode(false);
      setResponseNotes("");
    } catch (err) {
      setUpdateError(err.message || "Unable to update ticket.");
    } finally {
      setSavingUpdate(false);
    }
  };

  const openReviewModal = (mode) => {
    setReviewMode(mode);
    setCorrectedCategory(ticket.corrected_category || "");
    setReviewNotes(ticket.review_notes || "");
    setReviewError("");
  };

  const openHelpdeskModal = () => {
    setHelpdeskMode(true);
    setUpdatedSeverity(ticket.urgency || "SEV3");
    setResponseNotes(ticket.response_notes || "");
    setUpdateError("");
  };

  if (loading) {
    return (
      <div className="loading-state" role="status">
        Loading ticket details...
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="error-state" role="alert">
        <h2>Unable to Load Ticket</h2>
        <p>{error || "Unable to load this ticket."}</p>
        <Link to="/tickets" className="button primary-button">
          Back to Tickets
        </Link>
      </div>
    );
  }

  return (
    <div className="ticket-details-page">
      <div className="details-header">
        <Link to="/tickets" className="back-link">
          <ArrowLeft size={16} aria-hidden="true" />
          Back to Tickets
        </Link>

        <div className="title-row">
          <h1>Ticket #{ticket.id}</h1>
          <span className={`status-badge ${ticket.decision?.toLowerCase()}`}>
            {ticket.decision}
          </span>
        </div>
      </div>

      <div className="details-grid">
        <div className="main-panel">
          <section className="detail-card">
            <h2>{ticket.subject || "No subject"}</h2>
            <div className="meta-text">
              Created: {formatDate(ticket.created_at)}
            </div>
            <hr />
            <div className="ticket-body">
              <p>{ticket.body}</p>
            </div>
          </section>

          {ticket.response && (
            <section className="detail-card auto-reply-card">
              <h3>Generated Reply</h3>
              <div className="response-content">
                <pre>{ticket.response}</pre>
              </div>
            </section>
          )}

          <section className="detail-card">
            <div className="card-header-actions">
              <h3>Human QA Review</h3>

              {ticket.analysis_correct === null && (
                <div className="action-buttons">
                  <button
                    type="button"
                    className="button success-button"
                    onClick={() => saveReview({ analysisCorrect: true })}
                    disabled={savingReview}
                  >
                    <Check size={14} aria-hidden="true" />
                    {savingReview ? "Saving..." : "Mark Correct"}
                  </button>

                  <button
                    type="button"
                    className="button danger-button"
                    onClick={() => openReviewModal("incorrect")}
                    disabled={savingReview}
                  >
                    <X size={14} aria-hidden="true" />
                    Mark Incorrect
                  </button>
                </div>
              )}
            </div>

            {reviewError && !reviewMode && (
              <div className="error-message" role="alert">
                {reviewError}
              </div>
            )}

            {ticket.analysis_correct !== null && (
              <div className="review-summary">
                <div
                  className={`review-badge ${
                    ticket.analysis_correct ? "correct" : "incorrect"
                  }`}
                >
                  {ticket.analysis_correct
                    ? "✓ AI Classification Approved"
                    : "✕ AI Classification Marked Incorrect"}
                </div>

                {ticket.corrected_category && (
                  <p>
                    <strong>Corrected Category:</strong>{" "}
                    {formatCategory(ticket.corrected_category)}
                  </p>
                )}

                {ticket.review_notes && (
                  <p>
                    <strong>Review Notes:</strong> {ticket.review_notes}
                  </p>
                )}

                <button
                  type="button"
                  className="button secondary-button edit-button"
                  onClick={() =>
                    openReviewModal(
                      ticket.analysis_correct ? "correct" : "incorrect",
                    )
                  }
                  disabled={savingReview}
                >
                  <Pencil size={12} aria-hidden="true" />
                  Edit Review
                </button>
              </div>
            )}
          </section>
        </div>

        <div className="side-panel">
          <section className="detail-card info-card">
            <h3>Classification Details</h3>

            <div className="info-row">
              <span className="label">Category:</span>
              <span className="value">{formatCategory(ticket.category)}</span>
            </div>

            <div className="info-row">
              <span className="label">Urgency:</span>
              <span className={`urgency-tag ${ticket.urgency?.toLowerCase()}`}>
                {ticket.urgency || "Unknown"}
              </span>
            </div>

            <div className="info-row">
              <span className="label">SLA Target:</span>
              <span className="value">
                <Clock3 size={13} aria-hidden="true" />
                {ticket.sla || SLA_MAP[ticket.urgency] || "Unknown"}
              </span>
            </div>

            <div className="info-row">
              <span className="label">Model Confidence:</span>
              <span className="value">{ticket.confidence ?? 0}%</span>
            </div>

            {ticket.is_suspicious && (
              <div className="info-row warning-row">
                <ShieldAlert size={16} aria-hidden="true" />
                Flagged as Suspicious
              </div>
            )}

            <hr />

            <div className="reason-section">
              <span className="label">Assessment Reason:</span>
              <p>{ticket.reason || "No reason provided."}</p>
            </div>
          </section>

          <section className="detail-card helpdesk-card">
            <div className="card-header-actions">
              <h3>Helpdesk Response</h3>
              <button
                type="button"
                className="button primary-button"
                onClick={openHelpdeskModal}
                disabled={savingUpdate}
              >
                {ticket.responded ? "Update Response" : "Respond / Resolve"}
              </button>
            </div>

            {ticket.responded ? (
              <div className="response-status">
                <span className="badge resolved">Responded</span>
                <p className="meta-text">
                  At: {formatDate(ticket.response_datetime)}
                </p>
                {ticket.response_notes && <p>{ticket.response_notes}</p>}
              </div>
            ) : (
              <p className="pending-text">Awaiting helpdesk response.</p>
            )}
          </section>
        </div>
      </div>

      {reviewMode && (
        <div className="modal-backdrop">
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-title"
          >
            <h3 id="review-title">
              {reviewMode === "correct"
                ? "Confirm Accurate Analysis"
                : "Correct AI Analysis"}
            </h3>

            {reviewError && (
              <div className="error-message" role="alert">
                {reviewError}
              </div>
            )}

            {reviewMode === "incorrect" && (
              <div className="form-group">
                <label htmlFor="corrected-category">
                  Select Correct Category *
                </label>
                <select
                  id="corrected-category"
                  value={correctedCategory}
                  onChange={(event) => setCorrectedCategory(event.target.value)}
                  disabled={savingReview}
                  required
                >
                  <option value="">-- Choose Category --</option>
                  {REVIEW_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {formatCategory(category)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="review-notes">Review Notes (Optional)</label>
              <textarea
                id="review-notes"
                rows={3}
                value={reviewNotes}
                onChange={(event) => setReviewNotes(event.target.value)}
                placeholder="Explain the review decision..."
                disabled={savingReview}
              />
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="button secondary-button"
                onClick={() => setReviewMode(null)}
                disabled={savingReview}
              >
                Cancel
              </button>

              <button
                type="button"
                className="button primary-button"
                disabled={
                  savingReview ||
                  (reviewMode === "incorrect" && !correctedCategory)
                }
                onClick={() =>
                  saveReview({
                    analysisCorrect: reviewMode === "correct",
                    category: correctedCategory,
                    notes: reviewNotes,
                  })
                }
              >
                {savingReview ? "Saving..." : "Save Feedback"}
              </button>
            </div>
          </div>
        </div>
      )}

      {helpdeskMode && (
        <div className="modal-backdrop">
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="helpdesk-title"
          >
            <h3 id="helpdesk-title">Update Helpdesk Response</h3>

            {updateError && (
              <div className="error-message" role="alert">
                {updateError}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="updated-severity">Urgency Level</label>
              <select
                id="updated-severity"
                value={updatedSeverity}
                onChange={(event) => setUpdatedSeverity(event.target.value)}
                disabled={savingUpdate}
              >
                {SEVERITY_OPTIONS.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity} ({SLA_MAP[severity]})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="response-notes">
                Response / Resolution Notes
              </label>
              <textarea
                id="response-notes"
                rows={4}
                value={responseNotes}
                onChange={(event) => setResponseNotes(event.target.value)}
                placeholder="Enter notes about how this ticket was resolved..."
                disabled={savingUpdate}
              />
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="button secondary-button"
                onClick={() => setHelpdeskMode(false)}
                disabled={savingUpdate}
              >
                Cancel
              </button>

              <button
                type="button"
                className="button primary-button"
                disabled={savingUpdate}
                onClick={saveHelpdeskUpdate}
              >
                {savingUpdate ? "Updating..." : "Save Response"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

async function getErrorMessage(response, fallback) {
  const data = await response.json().catch(() => null);

  return typeof data?.detail === "string"
    ? data.detail
    : `${fallback} (${response.status})`;
}

function normalizeTicket(record) {
  if (
    !record ||
    typeof record !== "object" ||
    Array.isArray(record) ||
    record.id === null ||
    record.id === undefined
  ) {
    throw new Error("The API returned an invalid ticket.");
  }

  return {
    ...record,
    analysis_correct:
      record.analysis_correct === true || record.analysis_correct === 1
        ? true
        : record.analysis_correct === false || record.analysis_correct === 0
          ? false
          : null,
    is_suspicious: record.is_suspicious === true || record.is_suspicious === 1,
    responded: record.responded === true || record.responded === 1,
  };
}

function formatCategory(category) {
  if (!category) return "Unassigned";

  return String(category)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value) {
  if (!value) return "Not recorded";

  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? "Invalid date" : date.toLocaleString();
}

export default TicketDetails;
