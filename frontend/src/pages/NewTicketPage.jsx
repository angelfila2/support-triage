import { useState } from "react";
import { ArrowRight, BookOpen, FileText, Mail, Route, ShieldCheck, Sparkles } from "lucide-react";
import EmailUploader from "../components/EmailUploader";
import EmailPreview from "../components/EmailPreview";
import TriageResult from "../components/TriageResult";
import LoadingSpinner from "../components/LoadingSpinner";
import { triageTicket } from "../services/api";
function NewTicketPage() {
  const [mode, setMode] = useState("manual");
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
  const analyze = async ticket => {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const data = await triageTicket(ticket.subject, ticket.body);
      setResult(data);
    } catch (err) {
      setError(err.message || "Unable to process this ticket.");
    } finally {
      setLoading(false);
    }
  };
  if (loading) return <LoadingSpinner />;
  if (result) return <TriageResult result={result} onReset={reset} />;
  return <div className="intake-page">
      <section className="hero">
        <span className="eyebrow">TICKET INTAKE</span>
        <h1>Good support starts here.</h1>
        <p>Create a request. Let AI find the context and the right next step.</p>
      </section>
      <div className="intake-grid"><section className="intake-card">
      <div className="intake-card-heading"><span className="intake-symbol"><FileText size={19} /></span><div><h2>New support request</h2><p>One issue per ticket keeps things moving.</p></div></div>
      {email ? <EmailPreview email={email} onAnalyze={() => analyze(email)} onClear={reset} loading={loading} /> : <>
          <div className="ticket-entry-modes" aria-label="Ticket entry mode">
            <button type="button" aria-pressed={mode === "upload"} onClick={() => setMode("upload")}><Mail size={15} /> Upload email</button>
            <button type="button" aria-pressed={mode === "manual"} onClick={() => setMode("manual")}><FileText size={15} /> Type ticket</button>
          </div>
          {mode === "upload" ? <EmailUploader onEmailLoaded={ticket => {
            setEmail(ticket);
            setError("");
          }} /> : <form className="manual-ticket-form" onSubmit={event => {
            event.preventDefault();
            if (!subject.trim() || !body.trim()) {
              setError("Subject and problem description are required.");
              return;
            }
            analyze({
              subject: subject.trim(),
              body: body.trim()
            });
          }}>
              <label htmlFor="ticket-subject">Subject</label>
              <input id="ticket-subject" value={subject} onChange={event => setSubject(event.target.value)} placeholder="e.g. Unable to sign in to my account" maxLength={500} required />
              <label htmlFor="ticket-body">Describe your issue</label>
              <textarea id="ticket-body" value={body} onChange={event => setBody(event.target.value)} maxLength={20000} placeholder="What happened? Include any steps you’ve already tried and how this is affecting you." rows={8} required />
              <div className="intake-submit"><span><Sparkles size={14} /> Classified and routed with AI</span><button type="submit" className="primary-button" disabled={loading}>Triage Ticket <ArrowRight size={15} /></button></div>
            </form>}
        </>}
      </section><aside className="intake-guide"><span className="guide-kicker"><Sparkles size={15} /> YOUR TRIAGE ASSISTANT</span><h2>From request to<br />the right response.</h2><p className="guide-intro">Less sorting. More solving.</p><ol>
        <li><span><FileText size={18} /></span><div><strong>Understand the issue</strong><p>Identify the intent, severity and confidence of the request.</p></div></li>
        <li><span><BookOpen size={18} /></span><div><strong>Find the right context</strong><p>Retrieve relevant guidance from the knowledge base.</p></div></li>
        <li><span><Route size={18} /></span><div><strong>Choose the next step</strong><p>Prepare a supported reply or escalate for a human review.</p></div></li>
      </ol><div className="guide-safety"><ShieldCheck size={18} /><p><strong>People stay in control.</strong> SEV1 and SEV2 incidents always escalate. Every decision can be reviewed.</p></div></aside></div>
      {error && <div className="api-error" role="alert"><strong>Unable to complete triage</strong><p>{error}</p></div>}
    </div>;
}
export default NewTicketPage;
