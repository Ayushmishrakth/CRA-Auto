import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

const PAGE_SIZE = 8;

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function FindingsTable({ findings = [] }) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [sortKey, setSortKey] = useState("severity");
  const [expanded, setExpanded] = useState(null);
  const [page, setPage] = useState(1);

  const rows = useMemo(() => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
    return findings
      .filter((finding) => {
        const matchesSeverity = severity === "all" || finding.severity === severity;
        const haystack = `${finding.parameter} ${finding.category} ${finding.status}`.toLowerCase();
        return matchesSeverity && haystack.includes(query.toLowerCase());
      })
      .sort((a, b) => {
        if (sortKey === "severity") {
          return (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9);
        }
        return String(a[sortKey] ?? "").localeCompare(String(b[sortKey] ?? ""));
      });
  }, [findings, query, severity, sortKey]);

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const currentRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Findings</h2>
          <p>{rows.length} controls matched current filters.</p>
        </div>
        <div className="table-tools">
          <input
            value={query}
            onChange={(event) => {
              setPage(1);
              setQuery(event.target.value);
            }}
            placeholder="Search findings"
          />
          <select
            value={severity}
            onChange={(event) => {
              setPage(1);
              setSeverity(event.target.value);
            }}
          >
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {["parameter", "category", "severity", "value", "status", "recommendation"].map(
                (key) => (
                  <th key={key}>
                    <button type="button" onClick={() => setSortKey(key)}>
                      {key.replace("_", " ")}
                    </button>
                  </th>
                )
              )}
              <th aria-label="Expand" />
            </tr>
          </thead>
          <tbody>
            {currentRows.map((finding) => (
              <tr key={finding.id}>
                <td>{finding.parameter}</td>
                <td>{finding.category}</td>
                <td>
                  <span className={`severity severity-${finding.severity}`}>
                    {finding.severity}
                  </span>
                </td>
                <td className="truncate-cell">{finding.value}</td>
                <td>{finding.status}</td>
                <td className="truncate-cell">{finding.recommendation}</td>
                <td>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => setExpanded(expanded === finding.id ? null : finding.id)}
                    aria-label="Expand finding"
                  >
                    {expanded === finding.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  {expanded === finding.id && (
                    <div className="expanded-row">
                      <strong>Assessment result</strong>
                      <p><strong>Expected:</strong> {finding.expected_value ?? "-"}</p>
                      <p><strong>Actual:</strong> {displayValue(finding.actual_value)}</p>
                      <p><strong>Reason:</strong> {finding.value}</p>
                      <strong>Recommendation</strong>
                      <p>{finding.recommendation || "No recommendation was generated from assessment results."}</p>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <button type="button" disabled={page === 1} onClick={() => setPage((v) => v - 1)}>
          Previous
        </button>
        <span>
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          disabled={page === totalPages}
          onClick={() => setPage((v) => v + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}
