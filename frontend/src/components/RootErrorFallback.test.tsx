import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders, screen } from "../test/render";
import { RootErrorFallback } from "./RootErrorFallback";

describe("RootErrorFallback", () => {
  const originalLocation = window.location;

  afterEach(() => {
    Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  });

  it("показывает заголовок, сообщение и кнопку перезагрузки (английские тексты)", () => {
    renderWithProviders(<RootErrorFallback />);

    expect(screen.getByRole("heading", { name: "Something went wrong" })).toBeInTheDocument();
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload page" })).toBeInTheDocument();
  });

  it("клик по кнопке вызывает window.location.reload", async () => {
    const reload = vi.fn();
    // MemoryRouter does not read window.location, so replacing the whole object is safe; afterEach
    // restores the original so it does not leak into other tests.
    Object.defineProperty(window, "location", { configurable: true, value: { reload } });
    const { user } = renderWithProviders(<RootErrorFallback />);

    await user.click(screen.getByRole("button", { name: "Reload page" }));

    expect(reload).toHaveBeenCalledTimes(1);
  });
});
