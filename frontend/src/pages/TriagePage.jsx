import { useState } from "react";

import EmailUploader from "../components/EmailUploader";
import EmailPreview from "../components/EmailPreview";
import TriageResult from "../components/TriageResult";
import LoadingSpinner from "../components/LoadingSpinner";

import { triageTicket } from "../services/triageApi";

// =========================================================
// TRIAGE PAGE
// =========================================================

function TriagePage({ onTriageComplete }) {
  const [email, setEmail] = useState(null);

  const [result, setResult] = useState(null);

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  // =====================================================
  // EMAIL LOADED
  // =====================================================

  const handleEmailLoaded = (loadedEmail) => {
    console.log("TriagePage received email:", loadedEmail);

    if (!loadedEmail) {
      console.error("EmailUploader returned no email.");

      return;
    }

    const emailData = {
      from: loadedEmail.from || "Unknown Sender",
      subject: loadedEmail.subject || "No Subject",

      body: loadedEmail.body || "",
    };

    console.log("Saving email to React state:", emailData);

    setEmail(emailData);

    setResult(null);

    setError("");
  };

  // =====================================================
  // ANALYSE EMAIL
  // =====================================================

  const analyzeEmail = async () => {
    if (!email) {
      return;
    }

    setLoading(true);

    setError("");

    setResult(null);

    try {
      const data = await triageTicket(email.subject, email.body);

      setResult(data);

      onTriageComplete?.(data);
    } catch (err) {
      console.error("Triage request failed:", err);

      setError(err.message || "Unable to connect to the triage API.");
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // RESET
  // =====================================================

  const reset = () => {
    setEmail(null);

    setResult(null);

    setError("");

    setLoading(false);
  };

  // =====================================================
  // DEBUG
  // =====================================================

  console.log("TriagePage email state:", email);

  // =====================================================
  // RESULT
  // =====================================================

  if (result) {
    return <TriageResult result={result} onReset={reset} />;
  }

  // =====================================================
  // LOADING
  // =====================================================

  if (loading) {
    return <LoadingSpinner />;
  }

  // =====================================================
  // EMAIL PREVIEW
  // =====================================================

  if (email) {
    return (
      <>
        <section className="hero">
          <span className="hero-badge">EMAIL PREVIEW</span>

          <h1>
            Review before
            <span> analysing.</span>
          </h1>

          <p>
            Check the extracted email content before sending it through the
            support ticket triage pipeline.
          </p>
        </section>

        <EmailPreview
          email={email}
          onAnalyze={analyzeEmail}
          onClear={reset}
          loading={loading}
        />

        {error && (
          <div className="api-error">
            <strong>Analysis failed</strong>

            <p>{error}</p>
          </div>
        )}
      </>
    );
  }

  // =====================================================
  // UPLOAD SCREEN
  // =====================================================

  return (
    <>
      <section className="hero">
        <span className="hero-badge">AI-POWERED SUPPORT</span>

        <h1>
          Triage support tickets
          <span> intelligently.</span>
        </h1>

        <p>
          <div className="triage-steps">
            <span>Step 1 : Download the email from their mailbox</span>
            <br></br>
            <span>Step 2 : Upload the email here</span>
            <br></br>
            <span>Step 3 : Let the AI pipeline do the rest!</span>
          </div>
        </p>
      </section>

      <EmailUploader onEmailLoaded={handleEmailLoaded} />

      {error && (
        <div className="api-error">
          <strong>Upload failed</strong>

          <p>{error}</p>
        </div>
      )}
    </>
  );
}

export default TriagePage;
