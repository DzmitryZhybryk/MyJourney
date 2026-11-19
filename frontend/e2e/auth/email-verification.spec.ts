import { expect, test } from "../fixtures";
import { WEBKIT_SECURE_COOKIE_REASON } from "../helpers/session";

/**
 * E2E: the email verification reminder (block F), a real-stack slice that MSW component tests
 * cannot reach.
 *
 * `EmailVerificationBanner.test.tsx` already covers render/dismiss in one jsdom context. Here is
 * only what needs a real browser and backend: a real JWT with `email_verified=false` raises the
 * banner, and the dismiss lives in a specific tab's sessionStorage (survives reload but is not
 * visible in a new tab).
 *
 * Successful verification (enter code -> 204 -> banner disappears, F6/G3) is deliberately NOT in
 * e2e: the code is stored encrypted with a backend-only key (unreachable) and the flow is covered by
 * `VerifyEmailDialog.test.tsx`. For the same reason (resend cooldown from the registration
 * auto-challenge) there is no "Send code -> stage 2" here.
 */

const BANNER_NAME = "Email verification reminder";
const PROFILE_BUTTON_NAME = "Open profile menu";
const DISMISS_BUTTON_NAME = "Dismiss reminder for this session";

test.describe("Email verification banner", () => {
  test("F1: после реальной регистрации (email не верифицирован) баннер виден", async ({ authedPage }) => {
    // The real backend issues a token with email_verified=false, so AuthContext raises the banner.
    await expect(authedPage.getByRole("region", { name: BANNER_NAME })).toBeVisible();
  });

  test("F4: dismiss (×) скрывает баннер и переживает reload той же вкладки", async ({ authedPage }) => {
    const banner = authedPage.getByRole("region", { name: BANNER_NAME });
    await expect(banner).toBeVisible();

    await authedPage.getByRole("button", { name: DISMISS_BUTTON_NAME }).click();
    await expect(banner).toBeHidden();

    // sessionStorage survives a tab reload, and the bootstrap refresh does not count as a "login"
    // (the dismiss flag is not reset), so the banner stays hidden.
    await authedPage.reload();
    await expect(authedPage.getByRole("button", { name: PROFILE_BUTTON_NAME })).toBeVisible();
    await expect(authedPage.getByRole("region", { name: BANNER_NAME })).toBeHidden();
  });

  test("F5: в новой вкладке баннер снова виден — dismiss живёт в sessionStorage вкладки", async ({
    authedPage,
    context,
    browserName,
  }) => {
    // A new tab restores the session from the refresh cookie (bootstrap); on webkit the cookie over
    // http is unavailable, so the test is skipped (see WEBKIT_SECURE_COOKIE_REASON).
    test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON);

    // Tab 1: hide the banner.
    await authedPage.getByRole("button", { name: DISMISS_BUTTON_NAME }).click();
    await expect(authedPage.getByRole("region", { name: BANNER_NAME })).toBeHidden();

    // A new tab: the cookie is shared (bootstrap restores the session) but sessionStorage is its own
    // and has no dismiss flag, so the reminder shows again.
    const newTab = await context.newPage();
    await newTab.goto("/");
    await expect(newTab.getByRole("button", { name: PROFILE_BUTTON_NAME })).toBeVisible();
    await expect(newTab.getByRole("region", { name: BANNER_NAME })).toBeVisible();

    await newTab.close();
  });
});
