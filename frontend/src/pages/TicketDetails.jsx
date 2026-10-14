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
      // Direct single-ticket endpoint
      const response = await fetch(
        `${API_URL}/api/tickets/${encodeURIComponent(ticketId)}`,
      );

      if (!response.ok) {
        throw new Error(`Unable to load ticket (${response.status})`);
      }

      const foundTicket = await response.json();
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
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Unable to save review.");
      }

      const updated = await response.json();
      setTicket(normalizeTicket(updated));
      setReviewMode(null);
      setCorrectedCategory("");
      setReviewNotes("");
    } catch (err) {
      console.error(err);
      setReviewError(err.message || "Unable to save review.");
    } finally {
      setSavingReview(false);
    }
  };

  const saveHelpdeskUpdate = async () => {
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
            response_notes: responseNotes,
          }),
        },
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Unable to update ticket.");
      }

      const updated = await response.json();
      setTicket(normalizeTicket(updated));
      setHelpdeskMode(false);
      setResponseNotes("");
    } catch (err) {
      console.error(err);
      setUpdateError(err.message || "Unable to update ticket.");
    } finally {
      setSavingUpdate(false);
    }
  };

  const openCorrectModal = () => {
    setReviewMode("correct");
    setCorrectedCategory("");
    setReviewNotes(ticket.review_notes || "");
    setReviewError("");
  };

  const openIncorrectModal = () => {
    setReviewMode("incorrect");
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
    return <div className="loading-state">Loading ticket details...</div>;
  }

  if (error || !ticket) {
    return (
      <div className="error-state">
        <h2>Ticket Not Found</h2>
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
          <ArrowLeft size={16} /> Back to Tickets
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
            <h2>{ticket.subject}</h2>
            <div className="meta-text">
              Created: {new Date(ticket.created_at).toLocaleString()}
            </div>
            <hr />
            <div className="ticket-body">
              <p>{ticket.body}</p>
            </div>
          </section>

          {ticket.response && (
            <section className="detail-card auto-reply-card">
              <h3>Generated Auto-Reply</h3>
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
                    className="button success-button"
                    onClick={() => saveReview({ analysisCorrect: true })}
                    disabled={savingReview}
                  >
                    <Check size={14} /> Mark Correct
                  </button>
                  <button
                    className="button danger-button"
                    onClick={openIncorrectModal}
                    disabled={savingReview}
                  >
                    <X size={14} /> Mark Incorrect
                  </button>
                </div>
              )}
            </div>

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
                  className="button secondary-button edit-button"
                  onClick={
                    ticket.analysis_correct
                      ? openCorrectModal
                      : openIncorrectModal
                  }
                >
                  <Pencil size={12} /> Edit Review
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
                {ticket.urgency}
              </span>
            </div>
            <div className="info-row">
              <span className="label">SLA Target:</span>
              <span className="value">
                <Clock3 size={13} /> {ticket.sla || SLA_MAP[ticket.urgency]}
              </span>
            </div>
            <div className="info-row">
              <span className="label">Confidence:</span>
              <span className="value">{ticket.confidence}%</span>
            </div>
            {ticket.is_suspicious && (
              <div className="info-row warning-row">
                <ShieldAlert size={16} /> Flagged as Suspicious
              </div>
            )}
            <hr />
            <div className="reason-section">
              <span className="label">AI Reasoning:</span>
              <p>{ticket.reason}</p>
            </div>
          </section>

          <section className="detail-card helpdesk-card">
            <div className="card-header-actions">
              <h3>Helpdesk Response</h3>
              <button
                className="button primary-button"
                onClick={openHelpdeskModal}
              >
                {ticket.responded ? "Update Response" : "Respond / Resolve"}
              </button>
            </div>
            {ticket.responded ? (
              <div className="response-status">
                <span className="badge resolved">Responded</span>
                <p className="meta-text">
                  At: {new Date(ticket.response_datetime).toLocaleString()}
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
          <div className="modal-card">
            <h3>
              {reviewMode === "correct"
                ? "Confirm Accurate Analysis"
                : "Correct AI Analysis"}
            </h3>
            {reviewError && <div className="error-message">{reviewError}</div>}

            {reviewMode === "incorrect" && (
              <div className="form-group">
                <label>Select Correct Category *</label>
                <select
                  value={correctedCategory}
                  onChange={(e) => setCorrectedCategory(e.target.value)}
                >
                  <option value="">-- Choose Category --</option>
                  {REVIEW_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {formatCategory(cat)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group">
              <label>Review Notes (Optional)</label>
              <textarea
                rows={3}
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Explain the review decision..."
              />
            </div>

            <div className="modal-actions">
              <button
                className="button secondary-button"
                onClick={() => setReviewMode(null)}
              >
                Cancel
              </button>
              <button
                className="button primary-button"
                disabled={savingReview}
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
          <div className="modal-card">
            <h3>Update Helpdesk Response</h3>
            {updateError && <div className="error-message">{updateError}</div>}

            <div className="form-group">
              <label>Urgency Level</label>
              <select
                value={updatedSeverity}
                onChange={(e) => setUpdatedSeverity(e.target.value)}
              >
                {SEVERITY_OPTIONS.map((sev) => (
                  <option key={sev} value={sev}>
                    {sev} ({SLA_MAP[sev]})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Response / Resolution Notes</label>
              <textarea
                rows={4}
                value={responseNotes}
                onChange={(e) => setResponseNotes(e.target.value)}
                placeholder="Enter notes about how this ticket was resolved..."
              />
            </div>

            <div className="modal-actions">
              <button
                className="button secondary-button"
                onClick={() => setHelpdeskMode(false)}
              >
                Cancel
              </button>
              <button
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

function normalizeTicket(record) {
  return {
    ...record,
    analysis_correct:
      record.analysis_correct === true || record.analysis_correct === 1
        ? true
        : record.analysis_correct === false || record.analysis_correct === 0
          ? false
          : null,
    is_suspicious: Boolean(record.is_suspicious),
    responded: Boolean(record.responded),
  };
}

function formatCategory(category) {
  if (!category) return "Unassigned";
  return category
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default TicketDetails;
