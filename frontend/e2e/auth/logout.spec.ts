import { expect, test } from "../fixtures";
import { getRefreshCookie, WEBKIT_SECURE_COOKIE_REASON } from "../helpers/session";

/**
 * E2E: logout (flow C).
 *
 * Real stack: a real `POST /v1/auth/logout/` (204) clears both the server HttpOnly cookie and the
 * local token. The menu item's presence (C1) is checked indirectly by clicking it.
 */
test.describe("Logout", () => {
  test("logout из меню профиля ведёт на /login и чистит сессию", async ({ authedPage, context, browserName }) => {
    test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON);

    // The refresh cookie is set at login; record "before" so the "after" assertion is meaningful.
    expect(await getRefreshCookie(context)).toBeDefined();

    await authedPage.getByRole("button", { name: "Open profile menu" }).click();
    await authedPage.getByRole("menuitem", { name: "Logout" }).click();

    await expect(authedPage).toHaveURL(/\/login$/u);

    const accessToken = await authedPage.evaluate(() => window.sessionStorage.getItem("access_token"));
    expect(accessToken).toBeNull();
    expect(await getRefreshCookie(context)).toBeUndefined();
  });

  test("logout идемпотентен офлайн — локально чистит сессию и ведёт на /login", async ({ authedPage, context }) => {
    // The network is off: the server logout will not arrive, but the frontend catch still clears the
    // token locally and navigates to /login (idempotency).
    await context.setOffline(true);

    await authedPage.getByRole("button", { name: "Open profile menu" }).click();
    await authedPage.getByRole("menuitem", { name: "Logout" }).click();

    await expect(authedPage).toHaveURL(/\/login$/u);

    const accessToken = await authedPage.evaluate(() => window.sessionStorage.getItem("access_token"));
    expect(accessToken).toBeNull();

    await context.setOffline(false);
  });
});
