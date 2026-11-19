import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server, TEST_CURRENT_USER } from "../../test/handlers";
import { makeAuthValue, renderWithProviders, screen } from "../../test/render";
import { ProfilePage } from "./ProfilePage";

// Mantine wraps the label and the description in one <label>, so the name starts with the label.
const CONSENT_LABEL = /^Product updates and news by email/u;

function renderProfile() {
  return renderWithProviders(<ProfilePage />, {
    route: "/profile",
    authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
  });
}

describe("ProfilePage — согласие на рассылку", () => {
  it("переключатель показывает сохранённое согласие", async () => {
    server.use(http.get("/v1/users/me/", () => HttpResponse.json({ ...TEST_CURRENT_USER, marketingEmailsConsent: true })));
    renderProfile();

    expect(await screen.findByRole("switch", { name: CONSENT_LABEL })).toBeChecked();
  });

  it("клик сохраняет согласие сразу, без кнопки, и шлёт только это поле", async () => {
    let sentBody: unknown;
    server.use(
      http.patch("/v1/users/me/", async ({ request }) => {
        sentBody = await request.json();
        return HttpResponse.json({ ...TEST_CURRENT_USER, marketingEmailsConsent: true });
      }),
    );
    const { user } = renderProfile();
    const toggle = await screen.findByRole("switch", { name: CONSENT_LABEL });
    expect(toggle).not.toBeChecked();

    await user.click(toggle);

    expect(await screen.findByRole("switch", { name: CONSENT_LABEL, checked: true })).toBeEnabled();
    expect(sentBody).toEqual({ marketingEmailsConsent: true });
  });

  it("при ошибке переключатель возвращается в сохранённое положение и показывает ошибку", async () => {
    server.use(
      http.patch("/v1/users/me/", () => HttpResponse.json({ code: "temporary", message: "" }, { status: 503 })),
    );
    const { user } = renderProfile();

    await user.click(await screen.findByRole("switch", { name: CONSENT_LABEL }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn't complete the request. Please try again a bit later.",
    );
    expect(screen.getByRole("switch", { name: CONSENT_LABEL })).not.toBeChecked();
  });
});
