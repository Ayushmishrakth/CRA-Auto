import { Component } from "react";

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[CRA] UI render failed", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="session-recovery">
        <div className="panel session-panel">
          <h1>CRA could not render this page</h1>
          <p>
            The frontend recovered from a screen-level error. Refresh the page or return to the dashboard.
          </p>
          <pre className="error-details">{this.state.error?.message || "Unknown UI error"}</pre>
          <div className="modal-actions">
            <button type="button" className="btn-secondary inline" onClick={() => window.location.reload()}>
              Refresh
            </button>
            <button type="button" className="primary-action" onClick={() => { window.location.href = "/dashboard"; }}>
              Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }
}
