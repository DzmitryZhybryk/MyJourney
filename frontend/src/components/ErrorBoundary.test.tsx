import { describe, expect, it, vi } from "vitest";

import { renderWithProviders, screen } from "../test/render";
import { ErrorBoundary } from "./ErrorBoundary";

/** A component that throws in render, to check the boundary catches it. */
function Boom(): never {
  throw new Error("render boom");
}

describe("ErrorBoundary", () => {
  it("рендерит детей, когда ошибки нет", () => {
    renderWithProviders(
      <ErrorBoundary fallback={<div>fallback</div>}>
        <div>healthy child</div>
      </ErrorBoundary>,
    );

    expect(screen.getByText("healthy child")).toBeInTheDocument();
    expect(screen.queryByText("fallback")).not.toBeInTheDocument();
  });

  it("показывает fallback, когда ребёнок падает в рендере", () => {
    // React prints the caught error to console.error; silence it to keep the output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});

    renderWithProviders(
      <ErrorBoundary fallback={<div>fallback shown</div>}>
        <Boom />
      </ErrorBoundary>,
    );

    expect(screen.getByText("fallback shown")).toBeInTheDocument();
  });
});
