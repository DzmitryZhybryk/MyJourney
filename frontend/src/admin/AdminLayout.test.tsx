import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import { makeVerifiedAuthValue, renderWithProviders, screen, within } from "../test/render";
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
        authValue: makeVerifiedAuthValue(),
      },
    );

    const link = screen.getByRole("link", { name: "Upload rules" });

    expect(link).toHaveAttribute("href", "/admin/media-config");
    expect(link).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText("media-config-section")).toBeInTheDocument();
  });

  it("правила загрузки — первый раздел меню, аккаунты — за ними", () => {
    renderWithProviders(
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route path="accounts" element={<div>accounts-section</div>} />
        </Route>
      </Routes>,
      {
        route: "/admin/accounts",
        authValue: makeVerifiedAuthValue(),
      },
    );

    const links = within(screen.getByRole("navigation", { name: "Admin" })).getAllByRole("link");

    expect(links.map((link) => link.textContent)).toEqual(["Upload rules", "Accounts"]);
    expect(links[1]).toHaveAttribute("aria-current", "page");
  });
});
