import { expect, test } from "@playwright/test";

import { makeUserData } from "../helpers/users";

/**
 * E2E: sign-up happy path (flow A, item A3).
 *
 * Registration goes through the real UI form (not a backend seed); that is the point of the test:
 * check the full path "filled the form -> 201 -> redirect to `/home` -> session token stored". A
 * unique user per run so it does not depend on the DB.
 *
 * Field micro-validation (A2) and 409 conflicts (L) are covered by the component
 * `SignUpPage.test.tsx` and are not duplicated here.
 */
test.describe("Sign up", () => {
  test("валидная регистрация ведёт на главную и сохраняет токен сессии", async ({ page }) => {
    const { username, email, password } = makeUserData();

    await page.goto("/signup");
    // exact: getByLabel matches a case-insensitive substring, and without it "Password" also catches
    // the eye button (aria-label "Toggle password visibility").
    await page.getByLabel("Username", { exact: true }).fill(username);
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    // The "Create account" button is disabled until the agreement is accepted.
    await page.getByRole("checkbox", { name: /I agree to the/u }).check();
    await page.getByRole("button", { name: "Create account" }).click();

    // The profile button lives only on HomePage: its appearance means successful signup and redirect to `/home`.
    await expect(page.getByRole("button", { name: "Open profile menu" })).toBeVisible();
    await expect(page).toHaveURL(/\/home$/u);

    // The access token is stored in sessionStorage (refresh is in the HttpOnly cookie, checked by block K).
    const accessToken = await page.evaluate(() => window.sessionStorage.getItem("access_token"));
    expect(accessToken).not.toBeNull();
  });
});
