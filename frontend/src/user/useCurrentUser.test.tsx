import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "./useCurrentUser";

/** A component calling useCurrentUser, to check the "only inside the provider" contract. */
function Consumer() {
  useCurrentUser();
  return null;
}

describe("useCurrentUser", () => {
  it("бросает, если вызван вне <CurrentUserProvider>", () => {
    // React prints the render error to console.error; silence it to keep the output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<Consumer />)).toThrow("useCurrentUser must be used within a <CurrentUserProvider>");
  });
});
