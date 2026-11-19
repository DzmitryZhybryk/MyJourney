import type { BrowserContext, Page } from "@playwright/test";

/** One element of `context.cookies()` (Playwright does not export the type by name). */
type Cookie = Awaited<ReturnType<BrowserContext["cookies"]>>[number];

/** The key under which the SPA stores the access token (see src/auth/tokenStore.ts). */
const ACCESS_TOKEN_KEY = "access_token";

/** Name of the HttpOnly cookie with the refresh token (see backend cookies.py). */
const REFRESH_COOKIE_NAME = "refresh_token";

/**
 * Reason for skipping cookie-dependent tests on WebKit.
 *
 * The refresh cookie is set with `Secure` while the dev/test stack runs over http://localhost.
 * Chromium/Firefox treat localhost as a secure context and store such a cookie over http, while
 * WebKit (Safari) rejects a Secure cookie over http even on localhost. So refresh from the cookie,
 * bootstrap and cookie attributes are unavailable on webkit against an http stack (they would
 * work over https in production). The other flows (on the sessionStorage token) run normally on webkit.
 */
export const WEBKIT_SECURE_COOKIE_REASON =
  "WebKit отвергает Secure-cookie по http://localhost — refresh/bootstrap-флоу недоступен против http-стека (нужен https)";

/**
 * Returns the context's refresh cookie, or undefined if there is none.
 *
 * The refresh cookie is HttpOnly, so it is not visible via `document.cookie`; read it only this way.
 */
export async function getRefreshCookie(context: BrowserContext): Promise<Cookie | undefined> {
  const cookies = await context.cookies();

  return cookies.find((cookie) => cookie.name === REFRESH_COOKIE_NAME);
}

/** Clears the page's sessionStorage, simulating "access token lost, refresh cookie alive". */
export async function clearSessionStorage(page: Page): Promise<void> {
  await page.evaluate(() => window.sessionStorage.clear());
}

/** Deletes all context cookies, simulating "the refresh cookie expired/was removed". */
export async function clearCookies(context: BrowserContext): Promise<void> {
  await context.clearCookies();
}

/** Reads the access token from sessionStorage (null if there is none). */
export async function getStoredAccessToken(page: Page): Promise<string | null> {
  return page.evaluate((key) => window.sessionStorage.getItem(key), ACCESS_TOKEN_KEY);
}

/**
 * Replaces the access token in sessionStorage with an arbitrary value.
 *
 * tokenStore reads the token memory-first, so the change applies only after `page.reload()`. Call
 * reload afterwards if the SPA must pick up the replaced token.
 */
export async function setStoredAccessToken(page: Page, token: string): Promise<void> {
  await page.evaluate(([key, value]) => window.sessionStorage.setItem(key, value), [ACCESS_TOKEN_KEY, token] as const);
}
