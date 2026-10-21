import BreakdownChart from "../components/BreakdownChart";
import { apiFetch } from "../services/api";
import {
  Activity,
  Bot,
  ChartNoAxesColumnIncreasing,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_URL } from "../config";

function InsightsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchTickets() {
      try {
        const response = await apiFetch(`${API_URL}/api/analytics`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Unable to load analytics (${response.status}).`);
        }

        const data = await response.json();

        if (!data || !Array.isArray(data.recent)) throw new Error("Invalid analytics data.");
        if (!controller.signal.aborted) setStats(data);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message || "Unable to load analytics.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchTickets();

    return () => controller.abort();
  }, []);

  const heading = (
    <div className="analytics-heading">
      <span className="eyebrow">SYSTEM INSIGHTS</span>
      <h1>Analytics</h1>
      <p>Overview of support ticket classifications and routing decisions.</p>
    </div>
  );

  if (loading) {
    return (
      <div className="analytics-page">
        {heading}

        <div className="loading-state" role="status">
          Loading analytics...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-page">
        {heading}

        <div className="api-error" role="alert">
          <strong>Unable to load analytics</strong>
          <p>{error}</p>
          <p>Check that the backend is running, then reload this page.</p>
        </div>
      </div>
    );
  }

  const total = stats.total;
  const autoReplies = stats.auto_replies;
  const escalations = stats.escalations;
  const averageConfidence = Math.round(stats.average_confidence);
  const categoryCounts = stats.categories;
  const recentTickets = stats.recent;

  return (
    <div className="analytics-page">
      {heading}

      <div className="analytics-metrics">
        <AnalyticsCard
          title="Total Tickets"
          value={total}
          icon={<Activity size={20} />}
        />

        <AnalyticsCard
          title="Auto Reply Decisions"
          value={autoReplies}
          icon={<Bot size={20} />}
        />

        <AnalyticsCard
          title="Escalated"
          value={escalations}
          icon={<TriangleAlert size={20} />}
        />

        <AnalyticsCard
          title="Avg. Model Confidence"
          value={`${averageConfidence}%`}
          icon={<ChartNoAxesColumnIncreasing size={20} />}
        />
      </div>

      <div className="analytics-grid">
        <section className="analytics-panel">
          <div className="panel-heading">
            <span className="eyebrow">CLASSIFICATION</span>
            <h2>Categories</h2>
          </div>

          <BreakdownChart label="Categories" rows={[
            ...Object.entries(categoryCounts).map(([category, count]) => ({ label: formatCategory(category), count })),
            ...(total > stats.completed ? [{ label: "Not yet triaged", count: total - stats.completed }] : [])
          ]} />
        </section>

        <section className="analytics-panel">
          <div className="panel-heading">
            <span className="eyebrow">ROUTING</span>
            <h2>Decision Breakdown</h2>
          </div>

          <BreakdownChart label="Routing decisions" rows={[
            { label: "Auto reply", count: autoReplies },
            { label: "Escalated", count: escalations },
            { label: "Not yet triaged", count: Math.max(0, total - autoReplies - escalations) }
          ]} />
        </section>
      </div>

      <section className="analytics-panel recent-panel">
        <div className="panel-heading">
          <span className="eyebrow">RECENT ACTIVITY</span>
          <h2>Recent Analyses</h2>
        </div>

        {total === 0 ? (
          <EmptyAnalytics />
        ) : (
          <div className="analytics-table-wrapper">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th scope="col">Category</th>
                  <th scope="col">Urgency</th>
                  <th scope="col">Decision</th>
                  <th scope="col">Confidence</th>
                </tr>
              </thead>

              <tbody>
                {recentTickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>{formatCategory(ticket.category)}</td>

                    <td>
                      <span className={`table-urgency ${ticket.urgency?.toLowerCase() || ""}`}>
                        {ticket.urgency || "Unknown"}
                      </span>
                    </td>

                    <td>
                      <span
                        className={`decision-badge ${
                          ticket.decision === "AUTO_REPLY"
                            ? "auto"
                            : "escalated"
                        }`}
                      >
                        {ticket.decision || "Unknown"}
                      </span>
                    </td>

                    <td>{ticket.confidence ?? 0}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function AnalyticsCard({ title, value, icon }) {
  return (
    <div className="analytics-card">
      <div className="analytics-card-top">
        <span>{title}</span>
        <div className="analytics-card-icon" aria-hidden="true">
          {icon}
        </div>
      </div>

      <strong>{value}</strong>
    </div>
  );
}

function EmptyAnalytics() {
  return (
    <div className="empty-analytics">
      <ChartNoAxesColumnIncreasing size={28} aria-hidden="true" />
      <p>No ticket data yet.</p>
      <span>Analyse some emails to populate this view.</span>
    </div>
  );
}

function formatCategory(category) {
  if (!category) return "Unknown";

  return String(category)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default InsightsPage;
