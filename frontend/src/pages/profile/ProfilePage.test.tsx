import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { getCurrentUserQueryKey } from "../../api/sdk";
import { AuthContext } from "../../auth/useAuth";
import { server, TEST_CURRENT_ACCOUNT, TEST_CURRENT_USER } from "../../test/handlers";
import { createTestQueryClient, makeAuthValue, renderWithProviders, screen, waitFor } from "../../test/render";
import { ProfilePage } from "./ProfilePage";

const VERIFIED = makeAuthValue({ isAuthenticated: true, emailVerified: true });

function renderProfile(options: Parameters<typeof renderWithProviders>[1] = { authValue: VERIFIED }) {
  return renderWithProviders(<ProfilePage />, { route: "/profile", ...options });
}

describe("ProfilePage — данные и имя", () => {
  it("показывает имя, логин и email; загрузка фото неактивна и помечена «Soon»", async () => {
    renderProfile();

    expect(await screen.findByRole("heading", { name: TEST_CURRENT_USER.displayName })).toBeInTheDocument();
    expect(await screen.findByText(TEST_CURRENT_ACCOUNT.username)).toBeInTheDocument();
    expect(screen.getByText(TEST_CURRENT_ACCOUNT.email)).toBeInTheDocument();
    const upload = screen.getByText("Upload photo");
    expect(upload).toHaveAttribute("aria-disabled", "true");
    expect(upload).toHaveTextContent("Soon");
  });

  it("имя правится на месте: Enter сохраняет обрезанное имя и кладёт ответ в кэш профиля", async () => {
    let sentBody: unknown;
    server.use(
      http.patch("/v1/users/me/", async ({ request }) => {
        sentBody = await request.json();
        return HttpResponse.json({ ...TEST_CURRENT_USER, displayName: "Alice D." });
      }),
    );
    const queryClient = createTestQueryClient();
    const { user } = renderProfile({ authValue: VERIFIED, queryClient });

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    const input = screen.getByRole("textbox", { name: "Name" });
    expect(input).toHaveFocus();
    await user.clear(input);
    await user.type(input, "  Alice D.  {Enter}");

    expect(await screen.findByRole("heading", { name: "Alice D." })).toBeInTheDocument();
    expect(sentBody).toEqual({ displayName: "Alice D." });
    expect(queryClient.getQueryData(getCurrentUserQueryKey())).toEqual({
      ...TEST_CURRENT_USER,
      displayName: "Alice D.",
    });
  });

  it("с клавиатуры: Enter на имени в фокусе открывает поле", async () => {
    const { user } = renderProfile();
    const name = await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName });

    name.focus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("textbox", { name: "Name" })).toHaveFocus();
  });

  it("Escape закрывает поле без запроса и оставляет прежнее имя", async () => {
    let patchCount = 0;
    server.use(
      http.patch("/v1/users/me/", () => {
        patchCount += 1;
        return HttpResponse.json(TEST_CURRENT_USER);
      }),
    );
    const { user } = renderProfile();

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    await user.type(screen.getByRole("textbox", { name: "Name" }), "x{Escape}");

    expect(screen.queryByRole("textbox", { name: "Name" })).toBeNull();
    expect(screen.getByRole("heading", { name: TEST_CURRENT_USER.displayName })).toBeInTheDocument();
    expect(patchCount).toBe(0);
  });

  it("неизменённое имя закрывает поле без запроса", async () => {
    let patchCount = 0;
    server.use(
      http.patch("/v1/users/me/", () => {
        patchCount += 1;
        return HttpResponse.json(TEST_CURRENT_USER);
      }),
    );
    const { user } = renderProfile();

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    await user.type(screen.getByRole("textbox", { name: "Name" }), " {Enter}");

    await waitFor(() => expect(screen.queryByRole("textbox", { name: "Name" })).toBeNull());
    expect(patchCount).toBe(0);
  });

  it.each([
    { typed: "   ", message: "Enter a name" },
    { typed: "a".repeat(51), message: "50 characters at most" },
  ])("валидация: «$message» под полем, запрос не уходит", async ({ typed, message }) => {
    let patchCount = 0;
    server.use(
      http.patch("/v1/users/me/", () => {
        patchCount += 1;
        return HttpResponse.json(TEST_CURRENT_USER);
      }),
    );
    const { user } = renderProfile();

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    const input = screen.getByRole("textbox", { name: "Name" });
    await user.clear(input);
    await user.type(input, `${typed}{Enter}`);

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(patchCount).toBe(0);
  });

  it("ошибка сервера показывается текстом из errors, поле остаётся открытым", async () => {
    server.use(
      http.patch("/v1/users/me/", () => HttpResponse.json({ code: "temporary", message: "" }, { status: 503 })),
    );
    const { user } = renderProfile();

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    await user.type(screen.getByRole("textbox", { name: "Name" }), "x{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn't complete the request. Please try again a bit later.",
    );
    expect(screen.getByRole("textbox", { name: "Name" })).toBeInTheDocument();
  });

  it("удалённый аккаунт при сохранении перезапрашивает профиль и разлогинивает", async () => {
    const goneBody = { code: "users.user_deleted", message: "" };
    server.use(http.patch("/v1/users/me/", () => HttpResponse.json(goneBody, { status: 410 })));
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: true });
    const { user } = renderProfile({ authValue });

    await user.click(await screen.findByRole("button", { name: TEST_CURRENT_USER.displayName }));
    server.use(http.get("/v1/users/me/", () => HttpResponse.json(goneBody, { status: 410 })));
    await user.type(screen.getByRole("textbox", { name: "Name" }), "x{Enter}");

    await waitFor(() => expect(authValue.clearSession).toHaveBeenCalled());
  });

  it("неподтверждённый email: отметка и кнопка, открывающая диалог", async () => {
    const authValue = makeAuthValue({ isAuthenticated: true, emailVerified: false });
    const { user } = renderProfile({ authValue });

    expect(await screen.findByText("Not verified")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(authValue.openVerifyDialog).toHaveBeenCalledOnce();
  });

  it("отметка «Not verified» исчезает, когда флаг сессии становится true", async () => {
    const unverified = makeAuthValue({ isAuthenticated: true, emailVerified: false });
    // The wrapper's auth value is fixed at mount; an inner provider lets rerender flip the flag.
    const { rerender } = renderWithProviders(
      <AuthContext.Provider value={unverified}>
        <ProfilePage />
      </AuthContext.Provider>,
      { route: "/profile", authValue: unverified },
    );
    expect(await screen.findByText("Not verified")).toBeInTheDocument();

    rerender(
      <AuthContext.Provider value={{ ...unverified, emailVerified: true }}>
        <ProfilePage />
      </AuthContext.Provider>,
    );

    expect(screen.queryByText("Not verified")).toBeNull();
    expect(screen.queryByRole("button", { name: "Verify" })).toBeNull();
  });

  it("сбой загрузки профиля показывает ошибку вместо карточки", async () => {
    server.use(http.get("/v1/users/me/", () => HttpResponse.json({ code: "temporary", message: "" }, { status: 503 })));
    renderProfile();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't load your profile. Refresh the page.");
  });
});
