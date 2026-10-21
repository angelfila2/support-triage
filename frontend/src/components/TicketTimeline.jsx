import { useEffect, useState } from "react";
import { ChevronDown, Clock3 } from "lucide-react";
import { apiFetch } from "../services/api";

export default function TicketTimeline({ ticket }) {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await apiFetch(`/api/tickets/${encodeURIComponent(ticket.id)}/timeline`, { signal: controller.signal });
        if (!response.ok) throw new Error("Unable to load ticket activity.");
        const data = await response.json();
        if (!controller.signal.aborted) { setEvents(data); setError(""); }
      } catch (error) {
        if (!controller.signal.aborted) setError(error.message);
      }
    }
    load();
    return () => controller.abort();
  }, [ticket]);
  return <details className="detail-card timeline-card expandable-card" aria-label="Ticket timeline">
    <summary><h3><Clock3 size={16} aria-hidden="true" /> Ticket timeline</h3><span className="expand-hint"><span className="when-closed">View details</span><span className="when-open">Hide details</span><ChevronDown size={18} aria-hidden="true" /></span></summary>
    <div className="expandable-content">
    {error ? <p role="alert">{error}</p> : <ol className="ticket-timeline">
      {events.map(event => <li key={event.id}>
        <strong>{event.title}</strong>
        {event.occurred_at ? <time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time> : <span className="timeline-time">Time not recorded</span>}
        <p>{event.description}</p>
      </li>)}
    </ol>}
    </div>
  </details>;
}
