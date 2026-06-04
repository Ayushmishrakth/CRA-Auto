import { Component } from "react";

export default class ReportPageErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    console.error("REPORT_PAGE_RUNTIME_EXCEPTION", error);
    console.error("REPORT_PAGE_COMPONENT_STACK", info?.componentStack);
    console.error("REPORT_PAGE_FAILED_PROPS", this.props.failedProps);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-banner">
          <strong>Report page failed to render.</strong>
          <p>{this.state.error.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}
