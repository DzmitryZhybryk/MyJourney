import type { Page } from "@playwright/test";

import { expect, test } from "../fixtures";
import { clearCookies, clearSessionStorage, getRefreshCookie, WEBKIT_SECURE_COOKIE_REASON } from "../helpers/session";

/**
 * E2E: session lifecycle: flow D (ProtectedRoute + bootstrap refresh) and K (refresh cookie
 * attributes).
 *
 * This is exactly the real-stack integration MSW component tests cannot reach: a real HttpOnly
 * refresh cookie and a real bootstrap refresh on reload/new tab. ProtectedRoute's render logic is
 * covered by `ProtectedRoute.test.tsx`.
 *
 * E1 (single-flight on 401 during a protected action) is deliberately NOT in e2e: its logic is
 * exhaustively and deterministically covered by `api/client.test.ts` (including "one /refresh/
 * for parallel calls"), and the only authed UI trigger (send-verification) depends on the resend
 * cooldown from the registration auto-challenge, which is flaky. D2 exercises real refresh token
 * rotation against the backend.
 */

const REFRESH_URL = "/v1/auth/refresh/";
const PROFILE_BUTTON_NAME = "Open profile menu";

/** Attaches a counter of POST `/refresh/` calls to the page; returns the array of URLs. */
function trackRefreshRequests(page: Page): string[] {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes(REFRESH_URL)) {
      requests.push(request.url());
    }
  });

  return requests;
}

test.describe("Session lifecycle", () => {
  test("D1: reload сохраняет сессию — остаёмся на /home", async ({ authedPage }) => {
    await authedPage.reload();

    await expect(authedPage.getByRole("button", { name: PROFILE_BUTTON_NAME })).toBeVisible();
    await expect(authedPage).toHaveURL(/\/home$/u);
  });

  test("D2: потеря access-токена → reload → bootstrap-refresh из cookie, ровно один /refresh/", async ({
    authedPage,
    browserName,
  }) => {
    test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON);

    // Clear only sessionStorage; the refresh cookie is alive. On reload the bootstrap sees "no token"
    // and restores the session from the cookie. StrictMode runs the effect twice, so single-flight gives ONE /refresh/.
    await clearSessionStorage(authedPage);
    const refreshRequests = trackRefreshRequests(authedPage);

    await authedPage.reload();

    await expect(authedPage.getByRole("button", { name: PROFILE_BUTTON_NAME })).toBeVisible();
    await expect(authedPage).toHaveURL(/\/home$/u);
    expect(refreshRequests).toHaveLength(1);
  });

  test("D3: потеря и токена, и cookie → reload → редирект на /login", async ({ authedPage, context }) => {
    await clearSessionStorage(authedPage);
    await clearCookies(context);

    await authedPage.reload();

    await expect(authedPage).toHaveURL(/\/login$/u);
  });

  test("D4: новая вкладка с живой cookie → bootstrap → /home", async ({ authedPage, context, browserName }) => {
    test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON);

    // authedPage is already logged in, so the refresh cookie lives in the context. A new tab has its
    // own sessionStorage (no token) but the cookie is shared, so the bootstrap refresh restores the session.
    await expect(authedPage).toHaveURL(/\/home$/u);

    const newTab = await context.newPage();
    // Open exactly the root, as a user does. After the bootstrap PublicOnlyRoute sees the restored
    // session and moves them from the public landing to the dashboard.
    await newTab.goto("/");

    await expect(newTab.getByRole("button", { name: PROFILE_BUTTON_NAME })).toBeVisible();
    await expect(newTab).toHaveURL(/\/home$/u);

    await newTab.close();
  });

  test("D5: аноним на «/» остаётся на публичном лендинге", async ({ page }) => {
    // "/" is the public zone, not the protected dashboard: an anonymous user sees the landing and is
    // not redirected. ProtectedRoute itself is checked in D6.
    await page.goto("/");

    await expect(page).toHaveURL(/\/$/u);
    // Recognize the landing by its single h1, not by button text: copy lives in i18n and changes,
    // while "the page has a level-one heading" is a structural invariant.
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("D6: аноним на защищённом /home → редирект на /login", async ({ page }) => {
    // A fresh context with no token and no cookie: ProtectedRoute redirects to /login.
    await page.goto("/home");

    await expect(page).toHaveURL(/\/login$/u);
  });

  test("K: refresh-cookie HttpOnly + SameSite=Lax + Secure, хранится на http://localhost", async ({
    authedPage,
    context,
    browserName,
  }) => {
    test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON);

    // authedPage guarantees a completed login, so the cookie is set.
    await expect(authedPage).toHaveURL(/\/home$/u);

    const refreshCookie = await getRefreshCookie(context);

    expect(refreshCookie).toBeDefined();
    expect(refreshCookie?.httpOnly).toBe(true);
    expect(refreshCookie?.sameSite).toBe("Lax");
    // Secure=true, yet the cookie is still stored on http://localhost (localhost is a secure context); this is K3.
    expect(refreshCookie?.secure).toBe(true);
  });
});
