import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAuth } from "./useAuth";

/** A component calling useAuth, to check the "only inside the provider" contract. */
function Consumer() {
  useAuth();
  return null;
}

describe("useAuth", () => {
  it("бросает, если вызван вне <AuthProvider>", () => {
    // React prints the render error to console.error; silence it to keep the output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<Consumer />)).toThrow("useAuth must be used within an <AuthProvider>");
  });
});
