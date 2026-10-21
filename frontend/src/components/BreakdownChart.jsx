import { useState } from "react";
import { ChartNoAxesColumnIncreasing, ChartPie } from "lucide-react";

const COLORS = ["#3157b7", "#b45309", "#087f70", "#7c3aed", "#be185d", "#475569"];

export default function BreakdownChart({ label, rows }) {
  const [view, setView] = useState("bar");
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  const segments = rows.map((row, index) => {
    const start = total ? rows.slice(0, index).reduce((sum, item) => sum + item.count, 0) / total * 100 : 0;
    const offset = start + (total ? row.count / total * 100 : 0);
    return `${COLORS[index % COLORS.length]} ${start}% ${offset}%`;
  });
  return <div className="breakdown-chart">
    <div className="chart-toggle" role="group" aria-label={`${label} chart type`}>
      <button type="button" aria-pressed={view === "bar"} onClick={() => setView("bar")}><ChartNoAxesColumnIncreasing size={16} /> Bar chart</button>
      <button type="button" aria-pressed={view === "pie"} onClick={() => setView("pie")}><ChartPie size={16} /> Pie chart</button>
    </div>
    {total === 0 ? <p className="chart-empty">No ticket data yet.</p> : <>
      {view === "pie" && <div className="pie-chart" role="img" aria-label={`${label}: ${rows.map(row => `${row.label}, ${row.count} tickets`).join("; ")}`} style={{background: `conic-gradient(${segments.join(",")})`}} />}
      <ul className="chart-legend">
        {rows.map((row, index) => <li key={row.label}>
          <div className="chart-label"><span><i style={{background: COLORS[index % COLORS.length]}} />{row.label}</span><strong>{row.count} <small>({Math.round(row.count / total * 100)}%)</small></strong></div>
          {view === "bar" && <div className="chart-bar-track" aria-hidden="true"><div style={{width: `${row.count / total * 100}%`, background: COLORS[index % COLORS.length]}} /></div>}
        </li>)}
      </ul>
    </>}
  </div>;
}
