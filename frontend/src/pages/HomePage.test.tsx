import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../test/handlers";
import { findMenuItem, makeAuthValue, renderRoutes, screen, waitFor } from "../test/render";
import type { AuthContextValue } from "../auth/useAuth";
import { HomePage } from "./HomePage";

const BANNER_MESSAGE =
  "Your email isn't verified yet. Some features may be limited until you confirm it.";

function renderHome(authValue: AuthContextValue) {
  return renderRoutes({
    element: <HomePage />,
    path: "/",
    landings: [{ path: "/login", label: "login-landing" }],
    authValue,
  });
}

describe("HomePage", () => {
  it("логотип ведёт сразу на /home, без хопа через редирект с корня", () => {
    renderHome(makeAuthValue({ isAuthenticated: true, emailVerified: true }));

    expect(screen.getByRole("link", { name: "MyJourney" })).toHaveAttribute("href", "/home");
  });

  it("logout: меню → Logout → очищает сессию и уводит на /login", async () => {
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: true });
    const { user } = renderHome(authValue);

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(await findMenuItem("Logout"));

    expect(await screen.findByText("login-landing")).toBeInTheDocument();
    expect(authValue.clearSession).toHaveBeenCalledOnce();
  });

  it("logout идемпотентен: при сетевой ошибке всё равно очищает сессию и уводит на /login", async () => {
    server.use(http.post("/v1/auth/logout/", () => HttpResponse.error()));
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: true });
    const { user } = renderHome(authValue);

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(await findMenuItem("Logout"));

    expect(await screen.findByText("login-landing")).toBeInTheDocument();
    expect(authValue.clearSession).toHaveBeenCalledOnce();
  });

  it("неверифицированный email: показывает баннер и пункт Verify email открывает диалог", async () => {
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: false });
    const { user } = renderHome(authValue);

    expect(screen.getByText(BANNER_MESSAGE)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(await findMenuItem("Verify email"));

    expect(authValue.openVerifyDialog).toHaveBeenCalled();
  });

  it("дата видна сразу, приветствие с displayName появляется после загрузки профиля", async () => {
    renderHome(makeAuthValue({ isAuthenticated: true, emailVerified: true }));

    // The date does not depend on the network and is there from the first render; the greeting line is not yet.
    expect(screen.getByText(/^[A-Za-z]+ · [A-Za-z]+ \d{4}$/u)).toBeInTheDocument();
    expect(screen.queryByText(/Hello,/u)).not.toBeInTheDocument();

    expect(await screen.findByText("Hello, traveler")).toBeInTheDocument();
  });

  it("ошибка загрузки профиля: дата остаётся, строка приветствия так и не появляется", async () => {
    server.use(
      http.get("/v1/users/me/", () =>
        HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 }),
      ),
    );

    renderHome(makeAuthValue({ isAuthenticated: true, emailVerified: true }));

    // Wait for the request to finish (the provider moves to error), then check the DOM.
    await waitFor(() => {
      expect(screen.getByText(/^[A-Za-z]+ · [A-Za-z]+ \d{4}$/u)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Hello,/u)).not.toBeInTheDocument();
  });

  it("верифицированный email: нет баннера и нет пункта Verify email", async () => {
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: true });
    const { user } = renderHome(authValue);

    expect(screen.queryByText(BANNER_MESSAGE)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    // Grab all items at once and check by text that Verify email is not among them.
    const names = (await screen.findAllByRole("menuitem")).map((item) => item.textContent);
    expect(names).toContain("Logout");
    expect(names).not.toContain("Verify email");
  });
});
