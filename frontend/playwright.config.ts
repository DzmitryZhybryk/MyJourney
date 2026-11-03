import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright e2e config.
 *
 * Tests run against a SEPARATE throwaway stack (`docker-compose.e2e.yaml`) that the root
 * `make test-e2e` brings up: the frontend on :5273 proxies `/v1` to the backend, Postgres lives in
 * tmpfs and is torn down after the run; the dev database (`make run`, :5173) is not
 * touched. So there is NO `webServer` here: the stack lifecycle belongs to the Makefile, not Playwright.
 *
 * The default baseURL is the throwaway stack's port (:5273), not the dev frontend's (:5173): a bare
 * `npm run e2e` must not accidentally hit the dev stack and pollute its DB. Overridable via
 * E2E_BASE_URL (`make test-e2e` sets it; e.g. for CI against another host).
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5273";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // The backend argon2-hashes the password on every register/login (~50ms+). At full parallelism this
  // saturates the CPU and some logins miss the default 5s expect timeout. Cap the workers and give
  // assertions extra time.
  workers: process.env.CI ? 2 : 4,
  expect: { timeout: 15000 },
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    // Pin the language: the i18next detector without localStorage falls back to navigator.language,
    // and en-US normalizes to `en`, so form labels match the test locators.
    locale: "en-US",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  // WebKit is in the matrix but its cookie-dependent tests are skipped selectively: WebKit rejects a
  // `Secure` cookie over http://localhost (Chromium/Firefox store it), so refresh from the cookie,
  // bootstrap and cookie attributes are unavailable on webkit against an http stack (they would work
  // over https in production). See `test.skip(browserName === "webkit", WEBKIT_SECURE_COOKIE_REASON)`
  // in the specs. The other flows (on the sessionStorage token) run normally on webkit.
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
