import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { getAccessToken } from "./tokenStore";
import { VerifyEmailDialog } from "./VerifyEmailDialog";
import { i18n } from "../i18n";
import ruErrors from "../locales/ru/errors.json";
import { makeAccessToken, server } from "../test/handlers";
import { act, renderWithProviders, screen } from "../test/render";
import type { UserEvent } from "@testing-library/user-event";

/** Mounts the dialog open with onClose/onVerified spies. */
function renderDialog() {
  const onClose = vi.fn();
  const onVerified = vi.fn();
  const view = renderWithProviders(
    <VerifyEmailDialog opened onClose={onClose} onVerified={onVerified} />,
  );

  return { ...view, onClose, onVerified };
}

/** Moves the dialog from the intro stage to code entry (Send code -> 202). */
async function gotoCodeStage(user: UserEvent) {
  await user.click(screen.getByRole("button", { name: "Send code" }));
  await screen.findByRole("button", { name: "Verify" });
}

/** Types the code one digit into each PinInput input. */
async function typeCode(user: UserEvent, code: string) {
  const inputs = screen.getAllByRole("textbox");
  for (let index = 0; index < code.length; index += 1) {
    await user.type(inputs[index], code[index]);
  }
}

describe("VerifyEmailDialog", () => {
  it("на стадии intro показывает пояснение и кнопки", () => {
    renderDialog();

    expect(
      screen.getByText(/We'll send a 6-digit code to your email/u),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Later" })).toBeInTheDocument();
  });

  it("кнопка Later закрывает диалог", async () => {
    const { user, onClose } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Later" }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("Send code (202) переводит на стадию ввода кода", async () => {
    const { user } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Send code" }));

    expect(
      await screen.findByText("We sent a code to your email. Enter the 6 digits below."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verify" })).toBeInTheDocument();
  });

  it("Send code в cooldown (429) показывает ошибку и остаётся на intro", async () => {
    server.use(
      http.post("/v1/auth/email/send-verification/", () =>
        HttpResponse.json({ code: "auth.challenge_resend_cooldown", message: "ru" }, { status: 429 }),
      ),
    );
    const { user } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Send code" }));

    expect(
      await screen.findByText("Please wait before resending the code"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Verify" })).not.toBeInTheDocument();
  });

  it("Send code при уже верифицированном email (409) синкает токен и закрывает диалог", async () => {
    const refreshedToken = makeAccessToken({ email_verified: true });
    server.use(
      http.post("/v1/auth/email/send-verification/", () =>
        HttpResponse.json({ code: "auth.email_already_verified", message: "ru" }, { status: 409 }),
      ),
      http.post("/v1/auth/refresh/", () =>
        HttpResponse.json({ accessToken: refreshedToken, tokenType: "bearer" }),
      ),
    );
    const { user, onClose, onVerified } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Send code" }));

    await vi.waitFor(() => expect(onVerified).toHaveBeenCalledOnce());
    expect(onClose).toHaveBeenCalledOnce();
    expect(getAccessToken()).toBe(refreshedToken);
  });

  it("на стадии кода пустой код даёт inline-ошибку без запроса", async () => {
    const { user, onVerified } = renderDialog();
    await gotoCodeStage(user);

    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(
      await screen.findByText("Enter the 6-digit code from the email."),
    ).toBeInTheDocument();
    expect(onVerified).not.toHaveBeenCalled();
  });

  it("неверный код (400) показывает ошибку и оставляет на стадии кода", async () => {
    server.use(
      http.post("/v1/auth/email/verify/", () =>
        HttpResponse.json({ code: "auth.verification_code_invalid", message: "ru" }, { status: 400 }),
      ),
    );
    const { user, onVerified } = renderDialog();
    await gotoCodeStage(user);

    await typeCode(user, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(await screen.findByText("Invalid verification code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verify" })).toBeInTheDocument();
    expect(onVerified).not.toHaveBeenCalled();
  });

  it("истёкший код (410) показывает ошибку и откатывает на intro", async () => {
    server.use(
      http.post("/v1/auth/email/verify/", () =>
        HttpResponse.json({ code: "auth.challenge_expired", message: "ru" }, { status: 410 }),
      ),
    );
    const { user } = renderDialog();
    await gotoCodeStage(user);

    await typeCode(user, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(
      await screen.findByText("The code has expired. Request a new one"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("исчерпанные попытки (429) показывают минуты до нового кода и откатывают на intro", async () => {
    server.use(
      http.post("/v1/auth/email/verify/", () =>
        HttpResponse.json(
          {
            code: "auth.challenge_attempts_exceeded",
            message: "ru",
            details: { retry_after_seconds: 481 },
          },
          { status: 429 },
        ),
      ),
    );
    const { user } = renderDialog();
    await gotoCodeStage(user);

    await typeCode(user, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(
      await screen.findByText("Too many attempts. You can request a new code in 9 min"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("исчерпанные попытки (429) без числа показывают общий текст, а не плейсхолдер", async () => {
    server.use(
      http.post("/v1/auth/email/send-verification/", () =>
        HttpResponse.json(
          { code: "auth.challenge_attempts_exceeded", message: "ru" },
          { status: 429 },
        ),
      ),
    );
    const { user } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Send code" }));

    expect(
      await screen.findByText("Too many attempts. You can request a new code later"),
    ).toBeInTheDocument();
  });

  it("минуты в ошибке переживают смену языка", async () => {
    i18n.addResourceBundle("ru", "errors", ruErrors, true, true);
    server.use(
      http.post("/v1/auth/email/send-verification/", () =>
        HttpResponse.json(
          {
            code: "auth.challenge_attempts_exceeded",
            message: "ru",
            details: { retry_after_seconds: 120 },
          },
          { status: 429 },
        ),
      ),
    );
    const { user } = renderDialog();
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await screen.findByText("Too many attempts. You can request a new code in 2 min");

    try {
      await act(async () => {
        await i18n.changeLanguage("ru");
      });

      expect(
        screen.getByText("Слишком много попыток. Новый код можно запросить через 2 мин"),
      ).toBeInTheDocument();
    } finally {
      await act(async () => {
        await i18n.changeLanguage("en");
      });
    }
  });

  it("верный код (204) синкает токен, зовёт onVerified и закрывает диалог", async () => {
    const refreshedToken = makeAccessToken({ email_verified: true });
    server.use(
      http.post("/v1/auth/refresh/", () =>
        HttpResponse.json({ accessToken: refreshedToken, tokenType: "bearer" }),
      ),
    );
    const { user, onClose, onVerified } = renderDialog();
    await gotoCodeStage(user);

    await typeCode(user, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await vi.waitFor(() => expect(onVerified).toHaveBeenCalledOnce());
    expect(onClose).toHaveBeenCalledOnce();
    expect(getAccessToken()).toBe(refreshedToken);
  });
});
