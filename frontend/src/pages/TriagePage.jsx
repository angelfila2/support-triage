import { useState } from "react";
import EmailUploader from "../components/EmailUploader";
import EmailPreview from "../components/EmailPreview";
import TriageResult from "../components/TriageResult";
import LoadingSpinner from "../components/LoadingSpinner";
import { triageTicket } from "../services/triageApi";

function TriagePage({ onTriageComplete }) {
  const [mode, setMode] = useState("upload");
  const [email, setEmail] = useState(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = () => {
    setEmail(null);
    setResult(null);
    setError("");
    setLoading(false);
  };

  const analyze = async (ticket) => {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const data = await triageTicket(ticket.subject, ticket.body);
      setResult(data);
      onTriageComplete?.(data);
    } catch (err) {
      setError(err.message || "Unable to process this ticket.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (result) return <TriageResult result={result} onReset={reset} />;

  return (
    <>
      <section className="hero">
        <span className="hero-badge">AI-POWERED SUPPORT</span>
        <h1>Triage support tickets<span> intelligently.</span></h1>
        <p>Describe one issue per ticket. Upload an email or enter the problem below.</p>
      </section>
      {email ? (
        <EmailPreview email={email} onAnalyze={() => analyze(email)} onClear={reset} loading={loading} />
      ) : (
        <>
          <div className="ticket-entry-modes" aria-label="Ticket entry mode">
            <button type="button" aria-pressed={mode === "upload"} onClick={() => setMode("upload")}>Upload email</button>
            <button type="button" aria-pressed={mode === "manual"} onClick={() => setMode("manual")}>Type ticket</button>
          </div>
          {mode === "upload" ? (
            <EmailUploader onEmailLoaded={(ticket) => { setEmail(ticket); setError(""); }} />
          ) : (
            <form className="manual-ticket-form" onSubmit={(event) => {
              event.preventDefault();
              if (!subject.trim() || !body.trim()) {
                setError("Subject and problem description are required.");
                return;
              }
              analyze({ subject: subject.trim(), body: body.trim() });
            }}>
              <label htmlFor="ticket-subject">Subject</label>
              <input id="ticket-subject" value={subject} onChange={(event) => setSubject(event.target.value)} maxLength={500} required />
              <label htmlFor="ticket-body">Describe your issue</label>
              <textarea id="ticket-body" value={body} onChange={(event) => setBody(event.target.value)} maxLength={20000} rows={8} required />
              <button type="submit" disabled={loading}>Triage Ticket</button>
            </form>
          )}
        </>
      )}
      {error && <div className="api-error" role="alert"><strong>Unable to complete triage</strong><p>{error}</p></div>}
    </>
  );
}

export default TriagePage;
