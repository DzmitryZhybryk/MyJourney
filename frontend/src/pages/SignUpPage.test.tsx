import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { i18n } from "../i18n";
import ruAuth from "../locales/ru/auth.json";
import { server, TEST_ACCESS_TOKEN } from "../test/handlers";
import { makeAuthValue, renderRoutes, screen } from "../test/render";
import { SignUpPage } from "./SignUpPage";

/** Mounts SignUpPage at /signup with a "/" landing marker to observe navigation. */
function renderSignup() {
  const authValue = makeAuthValue({ setAccessToken: vi.fn() });
  const view = renderRoutes({
    element: <SignUpPage />,
    path: "/signup",
    landings: [{ path: "/home", label: "home-landing" }],
    authValue,
  });

  return { ...view, authValue };
}

const termsCheckbox = { name: /I agree to the/u };

describe("SignUpPage", () => {
  it("валидная регистрация передаёт токен в auth и ведёт на главную", async () => {
    const { user, authValue } = renderSignup();

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("home-landing")).toBeInTheDocument();
    expect(authValue.setAccessToken).toHaveBeenCalledWith(TEST_ACCESS_TOKEN);
  });

  it("username и email уходят на бэк без пробелов по краям", async () => {
    let body: unknown = null;
    server.use(
      http.post("/v1/auth/register/", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ accessToken: TEST_ACCESS_TOKEN, tokenType: "bearer" }, { status: 201 });
      }),
    );
    const { user } = renderSignup();

    await user.type(screen.getByLabelText("Username"), "  alice  ");
    await user.type(screen.getByLabelText("Email"), "  alice@example.com  ");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("home-landing")).toBeInTheDocument();
    expect(body).toMatchObject({ username: "alice", email: "alice@example.com" });
  });

  it("кнопка отправки заблокирована, пока не заполнены поля и не приняты условия", async () => {
    const { user } = renderSignup();

    expect(screen.getByRole("button", { name: "Create account" })).toBeDisabled();

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");

    // The fields are filled but consent is missing: the button stays disabled.
    expect(screen.getByRole("button", { name: "Create account" })).toBeDisabled();

    await user.click(screen.getByRole("checkbox", termsCheckbox));

    expect(screen.getByRole("button", { name: "Create account" })).toBeEnabled();
  });

  it("невалидные поля дают сообщения под полями и не отправляют запрос", async () => {
    const { user, authValue } = renderSignup();

    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await user.type(screen.getByLabelText("Username"), "ab");
    await user.type(screen.getByLabelText("Email"), "nope");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Username must be at least 3 characters")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
    expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
    expect(authValue.setAccessToken).not.toHaveBeenCalled();
  });

  it("уже показанная ошибка валидации переключается на новый язык", async () => {
    i18n.addResourceBundle("ru", "auth", ruAuth, true, true);
    const { user } = renderSignup();

    try {
      await user.click(screen.getByRole("checkbox", termsCheckbox));
      // Username is deliberately too short (an error is needed); the other fields only unlock the
      // button: it waits for the form to be filled, and submit checks validity.
      await user.type(screen.getByLabelText("Username"), "ab");
      await user.type(screen.getByLabelText("Email"), "alice@example.com");
      await user.type(screen.getByLabelText("Password"), "s3cret-pass");
      await user.click(screen.getByRole("button", { name: "Create account" }));

      expect(await screen.findByText("Username must be at least 3 characters")).toBeInTheDocument();

      await i18n.changeLanguage("ru");

      // The error was shown in en, the language switched: without re-validation the text became ru.
      expect(
        await screen.findByText("Имя пользователя должно содержать минимум 3 символа"),
      ).toBeInTheDocument();
    } finally {
      await i18n.changeLanguage("en");
    }
  });

  it("слишком длинные поля дают max-length ошибки и не отправляют запрос", async () => {
    const { user, authValue } = renderSignup();

    // Paste, not per-character typing: this checks the LENGTH LIMIT, and how text gets into the
    // field is irrelevant. `user.type` sends a full event cycle per character; at 352 characters the
    // test exceeded the default 5 seconds under a full coverage run and dragged the next test down.
    const fill = async (label: string, value: string) => {
      await user.click(screen.getByLabelText(label));
      await user.paste(value);
    };

    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await fill("Username", "a".repeat(51));
    await fill("Email", `${"a".repeat(250)}@example.com`);
    await fill("Password", "a".repeat(51));
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Username must be at most 50 characters")).toBeInTheDocument();
    expect(screen.getByText("Email is too long")).toBeInTheDocument();
    expect(screen.getByText("Password must be at most 50 characters")).toBeInTheDocument();
    expect(authValue.setAccessToken).not.toHaveBeenCalled();
  });

  it("конфликт email (409) показывает ошибку под полем Email", async () => {
    server.use(
      http.post("/v1/auth/register/", () =>
        HttpResponse.json(
          {
            code: "auth.email_already_registered",
            message: "русский текст бэка",
            details: { field: "email" },
          },
          { status: 409 },
        ),
      ),
    );
    const { user, authValue } = renderSignup();

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Email"), "taken@example.com");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("This email is already registered")).toBeInTheDocument();
    expect(authValue.setAccessToken).not.toHaveBeenCalled();
    expect(screen.queryByText("home-landing")).not.toBeInTheDocument();
  });

  it("конфликт username (409) показывает ошибку под полем Username", async () => {
    server.use(
      http.post("/v1/auth/register/", () =>
        HttpResponse.json(
          {
            code: "auth.username_already_taken",
            message: "русский текст бэка",
            details: { field: "username" },
          },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderSignup();

    await user.type(screen.getByLabelText("Username"), "taken");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "s3cret-pass");
    await user.click(screen.getByRole("checkbox", termsCheckbox));
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("This username is already taken")).toBeInTheDocument();
  });
});
