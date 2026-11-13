/**
 * The "email verification banner dismissed" flag lives in sessionStorage, so a dismiss lasts for
 * the tab. sessionStorage survives logout and a new signup in the same tab, so login and signup
 * reset the flag (`resetVerifyBannerDismissed`) to keep it from leaking between accounts.
 */

const DISMISS_STORAGE_KEY = "verify-banner-dismissed";

/** Whether the banner was dismissed in this tab's session. */
export function isVerifyBannerDismissed(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/** Marks the banner as dismissed for this tab's session. */
export function dismissVerifyBanner(): void {
  try {
    sessionStorage.setItem(DISMISS_STORAGE_KEY, "1");
  } catch {
    // sessionStorage unavailable (private mode / disabled): the dismiss is not persisted.
  }
}

/** Clears the dismissed flag; called on login/signup (a new session). */
export function resetVerifyBannerDismissed(): void {
  try {
    sessionStorage.removeItem(DISMISS_STORAGE_KEY);
  } catch {
    // sessionStorage unavailable: nothing to clear.
  }
}
