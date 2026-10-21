import { useState } from "react";
import { apiFetch } from "../services/api";

const STATUSES = {
  open: "Open",
  responded_waiting_info: "Responded (waiting for user info)",
  responded_awaiting_confirmation: "Responded (awaiting user confirmation)",
  responded_closed: "Responded (closed)",
};

export default function HelpdeskUpdateForm({ ticket, onSaved }) {
  const current = ticket.helpdesk_status || "open";
  const [selected, setSelected] = useState(current);
  const [notes, setNotes] = useState("");
  const [urgency, setUrgency] = useState(ticket.urgency || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function save(event) {
    event.preventDefault();
    if (!notes.trim() || saving) return;
    setSaving(true);
    setError("");
    try {
      const response = await apiFetch(`/api/tickets/${encodeURIComponent(ticket.id)}/status`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ helpdesk_status: selected, response_notes: notes.trim(), urgency: urgency || null }),
      });
      if (!response.ok) throw new Error(`Unable to save helpdesk update (${response.status}).`);
      const record = await response.json();
      setNotes("");
      onSaved(record);
    } catch (error) {
      setError(error.message);
    } finally {
      setSaving(false);
    }
  }
  return <form className="helpdesk-update-form" onSubmit={save}>
    <p className={`helpdesk-status-label ${current}`}>{STATUSES[current]}</p>
    {ticket.response_notes && <p className="latest-helpdesk-note"><strong>Last note:</strong> {ticket.response_notes}</p>}
    <label htmlFor="helpdesk-status">Ticket status</label>
    <select id="helpdesk-status" value={selected} onChange={event => setSelected(event.target.value)} disabled={saving}>
      {Object.entries(STATUSES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    <label htmlFor="helpdesk-urgency">Urgency</label>
    <select id="helpdesk-urgency" value={urgency} onChange={event => setUrgency(event.target.value)} disabled={saving}>
      <option value="">{ticket.urgency ? "Keep current urgency" : "Not assigned"}</option>
      {["SEV1", "SEV2", "SEV3", "SEV4", "SEV5"].map(value => <option key={value} value={value}>{value}</option>)}
    </select>
    <label htmlFor="helpdesk-note">Update note (required)</label>
    <textarea id="helpdesk-note" rows={4} required maxLength={5000} value={notes} onChange={event => setNotes(event.target.value)} disabled={saving} placeholder="Explain your reply, status change, or next step…" />
    <p className="status-help">Choose “Responded” after sending your reply. This records the status; no email is sent.</p>
    {error && <p role="alert" className="copy-error">{error}</p>}
    <button type="submit" className="primary-button" disabled={saving || !notes.trim()}>{saving ? "Saving…" : "Save update"}</button>
  </form>;
}
