import {
  CheckCircle2,
  AlertTriangle,
  Copy,
  RotateCcw,
  ShieldAlert,
  ArrowLeft,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
function TriageResult({ result, onReset }) {
  const navigate = useNavigate();
  const copyResponse = async () => {
    if (!result.response) return;

    await navigator.clipboard.writeText(result.response);
  };

  const confidence =
    typeof result.confidence === "number" ? result.confidence : 0;

  const decision = result.decision || "UNKNOWN";
  const isAutoReply = decision === "AUTO_REPLY";
  const isEscalate = decision === "ESCALATE";

  const decisionClass = isAutoReply
    ? "auto-reply"
    : isEscalate
      ? "escalate"
      : "";

  return (
    <div className="result-container">
      <div className="result-heading">
        <div>
          <span className="eyebrow">ANALYSIS COMPLETE</span>
          <h2>Triage Result</h2>
        </div>

        <button className="secondary-button" onClick={onReset}>
          <RotateCcw size={17} />
          New Email
        </button>
        <button
          className="ticket-back-button"
          onClick={() => navigate("/tickets")}
        >
          <ArrowLeft size={15} />
          All tickets
        </button>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <span>Category</span>
          <strong>{result.category?.replaceAll("_", " ") || "Unknown"}</strong>
        </div>

        <div className="metric-card">
          <span>Urgency</span>
          <strong className={`urgency ${result.urgency || ""}`}>
            {result.urgency || "Unknown"}
          </strong>
        </div>

        <div className="metric-card">
          <span>Confidence</span>
          <strong>
            {result.category === "other" ? "N/A" : `${confidence}%`}
          </strong>

          <div className="confidence-track">
            <div
              className="confidence-fill"
              style={{
                width: `${Math.min(Math.max(confidence, 0), 100)}%`,
              }}
            />
          </div>
        </div>
      </div>

      <div className={`decision-card ${decisionClass}`}>
        <div className="decision-icon">
          {isAutoReply ? (
            <CheckCircle2 size={26} />
          ) : (
            <AlertTriangle size={26} />
          )}
        </div>

        <div>
          <span>Recommended Action</span>
          <h3>{decision.replaceAll("_", " ")}</h3>
        </div>
      </div>

      {result.is_suspicious && (
        <div className="suspicious-warning">
          <ShieldAlert size={20} />

          <div>
            <strong>Suspicious content detected</strong>
            <p>
              This ticket may contain prompt injection or unsafe instructions.
            </p>
          </div>
        </div>
      )}

      <div className="card reason-card">
        <span className="eyebrow">REASONING</span>
        <p>{result.reason || "No reasoning provided."}</p>
      </div>

      {result.response && (
        <div className="card response-card">
          <div className="response-header">
            <div>
              <span className="eyebrow">GENERATED RESPONSE</span>
              <h3>Suggested Reply</h3>
            </div>

            <button className="secondary-button" onClick={copyResponse}>
              <Copy size={17} />
              Copy
            </button>
          </div>

          <div className="generated-response">{result.response}</div>
        </div>
      )}
    </div>
  );
}

export default TriageResult;
