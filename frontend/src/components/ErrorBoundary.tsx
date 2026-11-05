import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { message: string | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { message: null };

  static getDerivedStateFromError(error: Error): State {
    return { message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("workspace crash", error.message, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.message) {
      return (
        <div className="pad">
          <p className="error-banner">Workspace failed to render. {this.state.message}</p>
          <button type="button" className="ghost" onClick={() => this.setState({ message: null })}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
