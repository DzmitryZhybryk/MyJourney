import { describe, expect, it } from "vitest";

import { breakStorage } from "../test/storage";
import { dismissVerifyBanner, isVerifyBannerDismissed, resetVerifyBannerDismissed } from "./verifyBannerStorage";

const DISMISS_STORAGE_KEY = "verify-banner-dismissed";

describe("verifyBannerStorage", () => {
  it("по умолчанию плашка не скрыта", () => {
    expect(isVerifyBannerDismissed()).toBe(false);
  });

  it("dismiss помечает плашку скрытой в sessionStorage", () => {
    dismissVerifyBanner();

    expect(isVerifyBannerDismissed()).toBe(true);
    expect(sessionStorage.getItem(DISMISS_STORAGE_KEY)).toBe("1");
  });

  it("reset снимает флаг скрытия", () => {
    dismissVerifyBanner();
    resetVerifyBannerDismissed();

    expect(isVerifyBannerDismissed()).toBe(false);
  });

  it("возвращает false, когда чтение из sessionStorage бросает", () => {
    breakStorage("getItem");

    expect(isVerifyBannerDismissed()).toBe(false);
  });

  it("не бросает, когда запись в sessionStorage недоступна", () => {
    breakStorage("setItem");

    expect(() => dismissVerifyBanner()).not.toThrow();
  });
});
