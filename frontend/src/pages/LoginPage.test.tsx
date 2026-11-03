import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { makeAccessToken, server, TEST_ACCESS_TOKEN } from "../test/handlers";
import { makeAuthValue, renderRoutes, screen } from "../test/render";
import { LoginPage } from "./LoginPage";

/** Mounts LoginPage at /login with a "/" landing marker to observe navigation. */
function renderLogin() {
  const authValue = makeAuthValue({ setAccessToken: vi.fn() });
  const view = renderRoutes({
    element: <LoginPage />,
    path: "/login",
    landings: [{ path: "/home", label: "home-landing" }],
    authValue,
  });

  return { ...view, authValue };
}

describe("LoginPage", () => {
  it("успешный логин передаёт токен в auth и ведёт на главную", async () => {
    const { user, authValue } = renderLogin();

    await user.type(screen.getByLabelText("Username or email"), "alice");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("home-landing")).toBeInTheDocument();
    expect(authValue.setAccessToken).toHaveBeenCalledWith(TEST_ACCESS_TOKEN);
  });

  it("логин уходит на бэк без пробелов по краям", async () => {
    let body: unknown = null;
    server.use(
      http.post("/v1/auth/login/", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ accessToken: TEST_ACCESS_TOKEN, tokenType: "bearer" }, { status: 200 });
      }),
    );
    const { user } = renderLogin();

    await user.type(screen.getByLabelText("Username or email"), "  alice  ");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("home-landing")).toBeInTheDocument();
    expect(body).toMatchObject({ login: "alice" });
  });

  it("кнопка отправки заблокирована, пока не заполнены оба поля", async () => {
    const { user } = renderLogin();

    expect(screen.getByRole("button", { name: "Log in" })).toBeDisabled();

    // Spaces do not count as filled: `canSubmit` compares login trimmed.
    await user.type(screen.getByLabelText("Username or email"), "   ");
    expect(screen.getByRole("button", { name: "Log in" })).toBeDisabled();

    await user.clear(screen.getByLabelText("Username or email"));
    await user.type(screen.getByLabelText("Username or email"), "alice");
    expect(screen.getByRole("button", { name: "Log in" })).toBeDisabled();

    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled();
  });

  it("неверные креды (401) показывают общую ошибку на уровне формы", async () => {
    server.use(
      http.post("/v1/auth/login/", () =>
        HttpResponse.json(
          { code: "auth.invalid_credentials", message: "русский текст бэка" },
          { status: 401 },
        ),
      ),
    );
    const { user, authValue } = renderLogin();

    await user.type(screen.getByLabelText("Username or email"), "alice");
    await user.type(screen.getByLabelText("Password"), "wrong-pass");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Incorrect username/email or password")).toBeInTheDocument();
    expect(authValue.setAccessToken).not.toHaveBeenCalled();
    expect(screen.queryByText("home-landing")).not.toBeInTheDocument();
  });

  it("во время запроса кнопка переходит в состояние загрузки", async () => {
    server.use(
      http.post("/v1/auth/login/", async () => {
        await delay("infinite");
        return HttpResponse.json({ accessToken: makeAccessToken(), tokenType: "bearer" });
      }),
    );
    const { user } = renderLogin();

    await user.type(screen.getByLabelText("Username or email"), "alice");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("button", { name: "Log in" })).toHaveAttribute(
      "data-loading",
      "true",
    );
  });
});
