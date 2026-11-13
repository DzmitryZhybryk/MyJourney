import { expect, test } from "@playwright/test";

import { loginViaUi, registerUser } from "../helpers/users";

/**
 * E2E: login happy path (flow B).
 *
 * The test user is seeded via the backend API (a fresh unique login per run) so the test does not
 * depend on DB state or tie the login test to the registration UI. The email stays unverified,
 * which by contract does not block login to `/home`.
 */
test.describe("Login", () => {
  test("валидный логин ведёт на дашборд и показывает меню профиля", async ({ page, request }) => {
    const { username, password } = await registerUser(request);

    await page.goto("/login");
    // exact: getByLabel matches a case-insensitive substring, and without it "Password" also catches
    // the eye button (aria-label "Toggle password visibility").
    await page.getByLabel("Username or email", { exact: true }).fill(username);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Log in" }).click();

    // The profile button lives only on HomePage: its appearance means a successful login and redirect to `/home`.
    await expect(page.getByRole("button", { name: "Open profile menu" })).toBeVisible();
    await expect(page).toHaveURL(/\/home$/u);
    // The dashboard's globe background is a separate flow: e2e/globe/persistent-globe.spec.ts.
  });

  test("логин по email (а не только username) ведёт на дашборд", async ({ page, request }) => {
    // The single identifier field accepts both username and email; the backend resolves it. Email is
    // checked here; username login is covered by the test above. loginViaUi waits for the profile button itself.
    const { email, password } = await registerUser(request);

    await loginViaUi(page, { login: email, password });

    await expect(page).toHaveURL(/\/home$/u);
  });
});
