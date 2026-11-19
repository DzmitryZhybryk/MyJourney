import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Catches render errors in the subtree and shows `fallback` instead of crashing the whole UI.
 *
 * React has no function form of a boundary, so this is a class. No logging on purpose (console
 * is banned; React prints the stack in dev anyway). The root boundary prevents a blank screen;
 * the local one (around `PersistentGlobeHost`) isolates WebGL/three.js failures without breaking
 * the form.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback;
    }

    return this.props.children;
  }
}
