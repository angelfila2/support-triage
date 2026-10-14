import {
  Activity,
  Bot,
  ChartNoAxesColumnIncreasing,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_URL } from "../config";

function AnalyticsPage() {
  const [tickets, setTickets] = useState([]);

  const fetchTickets = async () => {
    try {
      const response = await fetch(`${API_URL}/api/tickets`);
      const data = await response.json();
      setTickets(data);
    } catch (error) {
      console.error("Error fetching tickets:", error);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const total = tickets.length;

  const autoReplies = tickets.filter(
    (ticket) => ticket.decision === "AUTO_REPLY",
  ).length;

  const escalations = tickets.filter(
    (ticket) => ticket.decision === "ESCALATE",
  ).length;

  const averageConfidence =
    total === 0
      ? 0
      : Math.round(
          tickets.reduce(
            (sum, ticket) => sum + (Number(ticket.confidence) || 0),
            0,
          ) / total,
        );

  const categoryCounts = tickets.reduce((counts, ticket) => {
    const category = ticket.category || "unknown";

    counts[category] = (counts[category] || 0) + 1;

    return counts;
  }, {});

  return (
    <div className="analytics-page">
      <div className="analytics-heading">
        <span className="eyebrow">SYSTEM INSIGHTS</span>

        <h1>Analytics</h1>

        <p>Overview of support ticket classifications and routing decisions.</p>
      </div>

      <div className="analytics-metrics">
        <AnalyticsCard
          title="Total Tickets"
          value={total}
          icon={<Activity size={20} />}
        />

        <AnalyticsCard
          title="Auto Replies"
          value={autoReplies}
          icon={<Bot size={20} />}
        />

        <AnalyticsCard
          title="Escalated"
          value={escalations}
          icon={<TriangleAlert size={20} />}
        />

        <AnalyticsCard
          title="Avg. Confidence"
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

          {Object.keys(categoryCounts).length === 0 ? (
            <EmptyAnalytics />
          ) : (
            <div className="category-list">
              {Object.entries(categoryCounts).map(([category, count]) => {
                const percentage = Math.round((count / total) * 100);

                return (
                  <div className="category-row" key={category}>
                    <div className="category-info">
                      <span>{formatCategory(category)}</span>

                      <strong>{count}</strong>
                    </div>

                    <div className="analytics-progress">
                      <div
                        className="analytics-progress-fill"
                        style={{
                          width: `${percentage}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className="analytics-panel">
          <div className="panel-heading">
            <span className="eyebrow">ROUTING</span>

            <h2>Decision Breakdown</h2>
          </div>

          {total === 0 ? (
            <EmptyAnalytics />
          ) : (
            <div className="routing-stats">
              <RoutingRow
                label="Auto Reply"
                value={autoReplies}
                total={total}
              />

              <RoutingRow label="Escalated" value={escalations} total={total} />
            </div>
          )}
        </section>
      </div>

      <section className="analytics-panel recent-panel">
        <div className="panel-heading">
          <span className="eyebrow">RECENT ACTIVITY</span>

          <h2>Recent Analyses</h2>
        </div>

        {tickets.length === 0 ? (
          <EmptyAnalytics />
        ) : (
          <div className="analytics-table-wrapper">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Urgency</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                </tr>
              </thead>

              <tbody>
                {tickets
                  .slice()
                  .reverse()
                  .slice(0, 10)
                  .map((ticket, index) => (
                    <tr key={index}>
                      <td>{formatCategory(ticket.category)}</td>

                      <td>
                        <span className="table-urgency">
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
                          {ticket.decision}
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

        <div className="analytics-card-icon">{icon}</div>
      </div>

      <strong>{value}</strong>
    </div>
  );
}

function RoutingRow({ label, value, total }) {
  const percentage = total === 0 ? 0 : Math.round((value / total) * 100);

  return (
    <div className="routing-row">
      <div>
        <span>{label}</span>
        <strong>{percentage}%</strong>
      </div>

      <div className="analytics-progress">
        <div
          className="analytics-progress-fill"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>

      <small>
        {value} of {total} tickets
      </small>
    </div>
  );
}

function EmptyAnalytics() {
  return (
    <div className="empty-analytics">
      <ChartNoAxesColumnIncreasing size={28} />

      <p>No ticket data yet.</p>

      <span>Analyse some emails to populate this view.</span>
    </div>
  );
}

function formatCategory(category) {
  if (!category) return "Unknown";

  return category
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default AnalyticsPage;
