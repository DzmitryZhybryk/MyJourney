import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import { makeAuthValue, renderWithProviders, screen } from "../test/render";
import { AdminLayout } from "./AdminLayout";

describe("AdminLayout", () => {
  it("меню разделов ведёт на раздел и подсвечивает открытый", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route path="media-config" element={<div>media-config-section</div>} />
        </Route>
      </Routes>,
      {
        route: "/admin/media-config",
        authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
      },
    );

    const link = screen.getByRole("link", { name: "Upload rules" });

    expect(link).toHaveAttribute("href", "/admin/media-config");
    expect(link).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText("media-config-section")).toBeInTheDocument();
  });
});
