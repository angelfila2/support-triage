import HelpdeskUpdateForm from "../components/HelpdeskUpdateForm";
import TicketTimeline from "../components/TicketTimeline";
import { apiFetch } from "../services/api";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ChevronDown, Check, Clock3, Clipboard, Pencil, ShieldAlert, Sparkles, UserRound, X } from "lucide-react";
import { API_URL } from "../config";
const REVIEW_CATEGORIES = ["password_reset", "billing_question", "shipping_delay", "login_issues", "other"];
const SLA_MAP = {
  SEV1: "4 hours",
  SEV2: "1 day",
  SEV3: "3 days",
  SEV4: "4 days",
  SEV5: "5 days"
};
function TicketDetailsPage() {
  const {
    ticketId
  } = useParams();

  // Reset page and form state when navigating to a different ticket.
  return <TicketDetailsPageContent key={ticketId} ticketId={ticketId} />;
}
function TicketDetailsPageContent({
  ticketId
}) {
  const [ticket, setTicket] = useState(null);
  const [retrying, setRetrying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewMode, setReviewMode] = useState(null);
  const [correctedCategory, setCorrectedCategory] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [updateError, setUpdateError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function fetchTicket() {
      try {
        const response = await apiFetch(`${API_URL}/api/tickets/${encodeURIComponent(ticketId)}`, {
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error(response.status === 404 ? "This ticket does not exist." : `Unable to load ticket (${response.status}).`);
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
    notes = null
  }) => {
    if (savingReview) return;
    if (!analysisCorrect && !REVIEW_CATEGORIES.includes(category)) {
      setReviewError("Select the correct category before saving.");
      return;
    }
    setSavingReview(true);
    setReviewError("");
    try {
      const response = await apiFetch(`${API_URL}/api/tickets/${encodeURIComponent(ticket.id)}/review`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          analysis_correct: analysisCorrect,
          corrected_category: analysisCorrect ? null : category,
          review_notes: notes?.trim() || null
        })
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Unable to save review."));
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
  const retryTicket = async () => {
    setRetrying(true);
    setError("");
    try {
      const response = await apiFetch(`${API_URL}/api/tickets/${encodeURIComponent(ticketId)}/retry`, {
        method: "POST"
      });
      if (!response.ok) throw new Error(await getErrorMessage(response, "Retry failed"));
      setTicket(normalizeTicket(await response.json()));
    } catch (err) {
      try {
        const response = await apiFetch(`${API_URL}/api/tickets/${encodeURIComponent(ticketId)}`);
        if (response.ok) setTicket(normalizeTicket(await response.json()));
      } catch {/* Preserve the saved ticket view when the network is unavailable. */}
      setUpdateError(err.message);
    } finally {
      setRetrying(false);
    }
  };
  const openReviewModal = mode => {
    setReviewMode(mode);
    setCorrectedCategory(ticket.corrected_category || "");
    setReviewNotes(ticket.review_notes || "");
    setReviewError("");
  };
  if (loading) {
    return <div className="loading-state" role="status">
        Loading ticket details...
      </div>;
  }
  if (error || !ticket) {
    return <div className="error-state" role="alert">
        <h2>Unable to Load Ticket</h2>
        <p>{error || "Unable to load this ticket."}</p>
        <Link to="/tickets" className="button primary-button">
          Back to Tickets
        </Link>
      </div>;
  }
  return <div className="ticket-details-page">
      <div className="details-header">
        <Link to="/tickets" className="back-link">
          <ArrowLeft size={16} aria-hidden="true" />
          Back to Tickets
        </Link>

        <div className="title-row">
          <div><span className="eyebrow">TICKET #{ticket.id}</span><h1>{ticket.subject || "Untitled request"}</h1></div>
          <span className={`status-badge ${ticket.decision?.toLowerCase()}`}>
            {ticket.decision === "AUTO_REPLY" ? "Auto reply" : ticket.decision === "ESCALATE" ? "Escalated" : "Awaiting triage"}
          </span>
        </div>
      </div>

      <section className={`processing-strip ${ticket.processing_status}`} aria-label="Processing status">
        <span className="process-badge"><i />{ticket.processing_status === "completed" ? "Triage complete" : `Processing: ${ticket.processing_status || "unknown"}`}</span>
        {ticket.processing_error && <p role="alert">{ticket.processing_error}</p>}
        {updateError && <p role="alert">{updateError}</p>}
        {["failed", "pending"].includes(ticket.processing_status) && <button type="button" onClick={retryTicket} disabled={retrying}>{retrying ? "Retrying..." : "Retry processing"}</button>}

      </section>
      <div className="details-grid">
        <div className="main-panel">
          <section className="detail-card">
            <div className="message-heading"><span className="message-avatar"><UserRound size={18} /></span><div><h2>Original request</h2><span>Submitted ticket</span></div><CopyButton text={`${ticket.subject || "Untitled request"}\n\n${ticket.body || ""}`} label="Copy original request" /></div>
            <div className="meta-text">
              Created: {formatDate(ticket.created_at)}
            </div>
            <hr />
            <div className="ticket-body">
              <p>{ticket.body}</p>
            </div>
          </section>

          {ticket.response && <section className="detail-card auto-reply-card">
              <div className="reply-card-heading"><span><Sparkles size={16} /> AI suggested reply</span><div className="reply-heading-actions"><small>Grounded in your knowledge base</small><CopyButton text={ticket.response} label="Copy AI suggested reply" /></div></div>
              <div className="response-content">
                <pre>{ticket.response}</pre>
              </div>
            </section>}

          <div className="review-response-grid">
          <section className="detail-card">
            <div className="card-header-actions">
              <h3>Review AI decision</h3>

              {ticket.analysis_correct === null && <div className="action-buttons">
                  <button type="button" className="button success-button" onClick={() => saveReview({
                analysisCorrect: true
              })} disabled={savingReview}>
                    <Check size={14} aria-hidden="true" />
                    {savingReview ? "Saving..." : "Mark Correct"}
                  </button>

                  <button type="button" className="button danger-button" onClick={() => openReviewModal("incorrect")} disabled={savingReview}>
                    <X size={14} aria-hidden="true" />
                    Mark Incorrect
                  </button>
                </div>}
            </div>

            {reviewError && !reviewMode && <div className="error-message" role="alert">
                {reviewError}
              </div>}

            {ticket.analysis_correct !== null && <div className="review-summary">
                <div className={`review-badge ${ticket.analysis_correct ? "correct" : "incorrect"}`}>
                  {ticket.analysis_correct ? "✓ AI Classification Approved" : "✕ AI Classification Marked Incorrect"}
                </div>

                {ticket.corrected_category && <p>
                    <strong>Corrected Category:</strong>{" "}
                    {formatCategory(ticket.corrected_category)}
                  </p>}

                {ticket.review_notes && <p>
                    <strong>Review Notes:</strong> {ticket.review_notes}
                  </p>}

                <button type="button" className="button secondary-button edit-button" onClick={() => openReviewModal(ticket.analysis_correct ? "correct" : "incorrect")} disabled={savingReview}>
                  <Pencil size={12} aria-hidden="true" />
                  Edit Review
                </button>
              </div>}
          </section>
          <section className="detail-card helpdesk-card">
            <h3>Helpdesk update</h3>
            <HelpdeskUpdateForm key={`${ticket.helpdesk_status}-${ticket.response_notes}`} ticket={ticket} onSaved={record => setTicket(normalizeTicket(record))} />
          </section>
          </div>
        </div>

        <div className="side-panel">
          <details className="detail-card info-card expandable-card">
            <summary><h3><Sparkles size={16} /> AI assessment</h3><span className="expand-hint"><span className="when-closed">View details</span><span className="when-open">Hide details</span><ChevronDown size={18} aria-hidden="true" /></span></summary>
            <div className="expandable-content">

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

            {ticket.is_suspicious && <div className="info-row warning-row">
                <ShieldAlert size={16} aria-hidden="true" />
                Flagged as Suspicious
              </div>}

            <hr />

            <div className="reason-section">
              <span className="label">Assessment Reason:</span>
              <p>{ticket.reason || "No reason provided."}</p>
            </div>
            </div>
          </details>

          <TicketTimeline ticket={ticket} />

        </div>
      </div>

      {reviewMode && <div className="modal-backdrop">
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="review-title">
            <h3 id="review-title">
              {reviewMode === "correct" ? "Confirm Accurate Analysis" : "Correct AI Analysis"}
            </h3>

            {reviewError && <div className="error-message" role="alert">
                {reviewError}
              </div>}

            {reviewMode === "incorrect" && <div className="form-group">
                <label htmlFor="corrected-category">
                  Select Correct Category *
                </label>
                <select id="corrected-category" value={correctedCategory} onChange={event => setCorrectedCategory(event.target.value)} disabled={savingReview} required>
                  <option value="">-- Choose Category --</option>
                  {REVIEW_CATEGORIES.map(category => <option key={category} value={category}>
                      {formatCategory(category)}
                    </option>)}
                </select>
              </div>}

            <div className="form-group">
              <label htmlFor="review-notes">Review Notes (Optional)</label>
              <textarea id="review-notes" rows={3} value={reviewNotes} onChange={event => setReviewNotes(event.target.value)} placeholder="Explain the review decision..." disabled={savingReview} />
            </div>

            <div className="modal-actions">
              <button type="button" className="button secondary-button" onClick={() => setReviewMode(null)} disabled={savingReview}>
                Cancel
              </button>

              <button type="button" className="button primary-button" disabled={savingReview || reviewMode === "incorrect" && !correctedCategory} onClick={() => saveReview({
            analysisCorrect: reviewMode === "correct",
            category: correctedCategory,
            notes: reviewNotes
          })}>
                {savingReview ? "Saving..." : "Save Feedback"}
              </button>
            </div>
          </div>
        </div>}

    </div>;
}
function CopyButton({ text, label }) {
  const [status, setStatus] = useState("");
  useEffect(() => {
    if (!status) return;
    const timer = setTimeout(() => setStatus(""), 3000);
    return () => clearTimeout(timer);
  }, [status]);
  async function copyText() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied");
    } catch {
      setStatus("Copy failed — select and copy the text manually.");
    }
  }
  return <div className="copy-control">
    <button type="button" className="copy-button" onClick={copyText} aria-label={label} title={label}>
      {status === "Copied" ? <Check size={16} aria-hidden="true" /> : <Clipboard size={16} aria-hidden="true" />}
      <span>{status === "Copied" ? "Copied" : "Copy"}</span>
    </button>
    <span className={status.startsWith("Copy failed") ? "copy-feedback copy-error" : "sr-only"} role="status">{status}</span>
  </div>;
}

async function getErrorMessage(response, fallback) {
  const data = await response.json().catch(() => null);
  return typeof data?.detail === "string" ? data.detail : data?.detail?.message || `${fallback} (${response.status})`;
}
function normalizeTicket(record) {
  if (!record || typeof record !== "object" || Array.isArray(record) || record.id === null || record.id === undefined) {
    throw new Error("The API returned an invalid ticket.");
  }
  return {
    ...record,
    analysis_correct: record.analysis_correct === true || record.analysis_correct === 1 ? true : record.analysis_correct === false || record.analysis_correct === 0 ? false : null,
    is_suspicious: record.is_suspicious === true || record.is_suspicious === 1,
    responded: record.responded === true || record.responded === 1
  };
}
function formatCategory(category) {
  if (!category) return "Unassigned";
  return String(category).replace(/_/g, " ").replace(/\b\w/g, character => character.toUpperCase());
}
function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Invalid date" : date.toLocaleString();
}
export default TicketDetailsPage;
