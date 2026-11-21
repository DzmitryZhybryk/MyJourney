import { describe, expect, it } from "vitest";

import { makeAuthValue, renderRoutes, screen } from "../test/render";
import { AdminRoute } from "./AdminRoute";

const CLAIMS = { sub: "user-1", email_verified: true, exp: 4_102_444_800 };

describe("AdminRoute", () => {
  it("администратор видит содержимое админки", async () => {
    renderRoutes({
      element: <AdminRoute>admin-content</AdminRoute>,
      path: "/admin",
      authValue: makeAuthValue({ isAuthenticated: true, claims: { ...CLAIMS, role: "admin" } }),
    });

    expect(await screen.findByText("admin-content")).toBeInTheDocument();
  });

  it("обычного пользователя уводит на главную", async () => {
    renderRoutes({
      element: <AdminRoute>admin-content</AdminRoute>,
      path: "/admin",
      landings: [{ path: "/home", label: "home-landing" }],
      authValue: makeAuthValue({ isAuthenticated: true, claims: { ...CLAIMS, role: "user" } }),
    });

    expect(await screen.findByText("home-landing")).toBeInTheDocument();
    expect(screen.queryByText("admin-content")).toBeNull();
  });
});
