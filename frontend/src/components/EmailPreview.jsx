import { ArrowRight, RotateCcw } from "lucide-react";

function EmailPreview({ email, onAnalyze, onClear, loading }) {
  if (!email) {
    return null;
  }

  return (
    <div className="email-preview">
      <div className="email-header">
        <div className="email-title">
          <div>
            <h2>Email Details</h2>
          </div>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={onClear}
          disabled={loading}
        >
          <RotateCcw size={14} />
          Choose Another
        </button>
      </div>

      {/* =================================================
          SUBJECT
      ================================================= */}

      <div className="email-field">
        <label>Subject</label>

        <div className="email-subject">{email.subject || "No Subject"}</div>
      </div>

      <div className="email-sender">
        <div className="email-field">
          <label>From</label>
          <div className="email-sender">{email.from || "Unknown Sender"}</div>
        </div>
      </div>

      <div className="email-field">
        <label>Message</label>

        <div className="email-body">{email.body || "No email body found."}</div>
      </div>

      {/* =================================================
          ACTIONS
      ================================================= */}

      <div className="email-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={onClear}
          disabled={loading}
        >
          <RotateCcw size={14} />
          Clear
        </button>

        <button
          type="button"
          className="analyze-button"
          onClick={onAnalyze}
          disabled={loading}
        >
          {loading ? "Analysing..." : "Analyse Email"}

          {!loading && <ArrowRight size={15} />}
        </button>
      </div>
    </div>
  );
}

export default EmailPreview;
