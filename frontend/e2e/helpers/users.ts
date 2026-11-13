import { randomUUID } from "node:crypto";

import { expect, type APIRequestContext, type Page } from "@playwright/test";

/** Credentials for a UI login: one identifier field (username OR email) plus a password. */
export interface Credentials {
  readonly login: string;
  readonly password: string;
}

/** Full data of a user registered through the API. */
export interface RegisteredUser {
  readonly username: string;
  readonly email: string;
  readonly password: string;
}

const DEFAULT_PASSWORD = "e2e-Password-123";

/**
 * Generates a unique username that is safe across parallel workers.
 *
 * Tests run `fullyParallel` in several processes and `Date.now()` alone can collide within a
 * millisecond, so a random uuid suffix is added.
 */
function uniqueUsername(): string {
  return `e2e_${Date.now()}_${randomUUID().slice(0, 8)}`;
}

/**
 * Generates new user data WITHOUT calling the API: unique username/email and a default password.
 *
 * Needed where registration goes through the UI form (not a backend seed) and the test requires a
 * unique set of input fields.
 */
export function makeUserData(): RegisteredUser {
  const username = uniqueUsername();

  return { username, email: `${username}@example.com`, password: DEFAULT_PASSWORD };
}

/**
 * Registers a fresh user via `/v1/auth/register/` and returns their data (username, email, password).
 *
 * A unique login per call means tests do not depend on DB state and run in parallel. The email
 * stays unverified, which by contract does not block login to `/home`.
 *
 * `request` is an APIRequestContext with the config baseURL (goes through the vite proxy to the backend).
 */
export async function registerUser(request: APIRequestContext): Promise<RegisteredUser> {
  const user = makeUserData();

  const response = await request.post("/v1/auth/register/", {
    data: {
      username: user.username,
      email: user.email,
      password: user.password,
      terms_accepted: true,
      marketing_emails_consent: false,
    },
  });
  expect(response.ok(), `register failed: ${response.status()} ${await response.text()}`).toBeTruthy();

  return user;
}

/**
 * Performs a UI login: fills the form at `/login` and waits for the dashboard (`/home`).
 *
 * `exact: true` is required: `getByLabel` matches a case-insensitive substring, and "Password"
 * without it also catches the eye button (aria-label "Toggle password visibility").
 */
export async function loginViaUi(page: Page, credentials: Credentials): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Username or email", { exact: true }).fill(credentials.login);
  await page.getByLabel("Password", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Log in" }).click();

  // The profile button lives only on HomePage: its appearance means a successful login and redirect to `/home`.
  await expect(page.getByRole("button", { name: "Open profile menu" })).toBeVisible();
}

/**
 * Registers a fresh user via the API and logs them in through the UI by username; returns the
 * logged-in user's data.
 *
 * Handy as a precondition for tests that need an already logged-in page but also timing
 * flexibility (when the `authedPage` fixture is not enough).
 */
export async function registerAndLogin(page: Page, request: APIRequestContext): Promise<RegisteredUser> {
  const user = await registerUser(request);
  await loginViaUi(page, { login: user.username, password: user.password });

  return user;
}
