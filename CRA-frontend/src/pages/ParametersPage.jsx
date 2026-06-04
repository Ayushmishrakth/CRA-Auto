import { Fragment, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { getRegistryParameters } from "../api/registryApi";
import LoadingSpinner from "../components/LoadingSpinner";

const PAGE_SIZE = 10;

function cleanLabel(value) {
  return String(value || "-").replace(/_/g, " ");
}

function getCheckDetails(item) {
  return item.pass_criteria || item.expected_output || item.portal_mapping || "Review the control against CRA readiness expectations.";
}

function TextBlock({ title, children }) {
  return (
    <article className="parameter-detail-block">
      <h3>{title}</h3>
      <p>{children || "-"}</p>
    </article>
  );
}

export default function ParametersPage() {
  const [parameters, setParameters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [domain, setDomain] = useState("all");
  const [expandedKey, setExpandedKey] = useState(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getRegistryParameters()
      .then((items) => {
        if (!cancelled) setParameters(items);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const domains = useMemo(
    () => [...new Set(parameters.map((item) => item.domain).filter(Boolean))].sort(),
    [parameters]
  );

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return parameters.filter((item) => {
      const matchesSeverity = severity === "all" || item.severity === severity;
      const matchesDomain = domain === "all" || item.domain === domain;
      const haystack = [
        item.display_name,
        item.technology,
        item.category,
        item.pass_criteria,
        item.fail_criteria,
        item.expected_output,
      ]
        .join(" ")
        .toLowerCase();
      return matchesSeverity && matchesDomain && (!term || haystack.includes(term));
    });
  }, [domain, parameters, query, severity]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const resetPaging = () => {
    setPage(1);
    setExpandedKey(null);
  };

  if (loading) {
    return <LoadingSpinner label="Loading parameters..." />;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <h1>Parameters</h1>
          <p>{parameters.length} Copilot readiness parameters.</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="metric-grid dashboard-metrics">
        <article className="metric-card">
          <span>Total parameters</span>
          <strong>{parameters.length}</strong>
        </article>
        <article className="metric-card">
          <span>Critical</span>
          <strong>{parameters.filter((item) => item.severity === "critical").length}</strong>
        </article>
        <article className="metric-card">
          <span>High</span>
          <strong>{parameters.filter((item) => item.severity === "high").length}</strong>
        </article>
        <article className="metric-card">
          <span>Domains</span>
          <strong>{domains.length}</strong>
        </article>
      </section>

      <section className="panel">
        <div className="table-tools wide parameter-tools">
          <label className="search-field">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => {
                resetPaging();
                setQuery(event.target.value);
              }}
              placeholder="Search parameter, criteria, output, or technology"
            />
          </label>
          <select
            value={severity}
            onChange={(event) => {
              resetPaging();
              setSeverity(event.target.value);
            }}
          >
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select
            value={domain}
            onChange={(event) => {
              resetPaging();
              setDomain(event.target.value);
            }}
          >
            <option value="all">All domains</option>
            {domains.map((item) => (
              <option value={item} key={item}>
                {cleanLabel(item)}
              </option>
            ))}
          </select>
        </div>

        <div className="table-wrap">
          <table className="data-table parameters-table">
            <thead>
              <tr>
                <th />
                <th>Parameter</th>
                <th>Technology</th>
                <th>Severity</th>
                <th>Domain</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => {
                const expanded = expandedKey === item.parameter_key;
                return (
                  <Fragment key={item.parameter_key}>
                    <tr key={item.parameter_key}>
                      <td>
                        <button
                          type="button"
                          className="icon-button"
                          onClick={() => setExpandedKey(expanded ? null : item.parameter_key)}
                          aria-label={expanded ? "Collapse parameter details" : "Expand parameter details"}
                        >
                          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </button>
                      </td>
                      <td>
                        <strong>{item.display_name}</strong>
                      </td>
                      <td>{item.technology || "-"}</td>
                      <td>
                        <span className={`status-pill severity-${item.severity || "info"}`}>
                          {item.severity || "info"}
                        </span>
                      </td>
                      <td>{cleanLabel(item.domain)}</td>
                      <td className="parameter-output">{item.expected_output || "-"}</td>
                    </tr>
                    {expanded && (
                      <tr className="parameter-details-row">
                        <td />
                        <td colSpan="5">
                          <div className="parameter-detail-grid">
                            <TextBlock title="Pass Criteria">{item.pass_criteria}</TextBlock>
                            <TextBlock title="Fail Criteria">{item.fail_criteria}</TextBlock>
                            <TextBlock title="Copilot Relation">{item.copilot_relevance}</TextBlock>
                            <TextBlock title="Validation Guidance">{getCheckDetails(item)}</TextBlock>
                            <TextBlock title="Recommendation">
                              {item.recommendation?.title}
                            </TextBlock>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {rows.length === 0 && <p className="muted-text">No parameters match the current filters.</p>}

        <div className="pagination">
          <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>
            Previous
          </button>
          <span>
            Page {page} of {totalPages} · {filtered.length} shown
          </span>
          <button
            type="button"
            disabled={page === totalPages}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
