import { describe, expect, it, vi } from "vitest";

import { breakStorage } from "../test/storage";
import { clearAccessToken, getAccessToken, setAccessToken, subscribeAccessToken } from "./tokenStore";

const STORAGE_KEY = "access_token";

describe("tokenStore", () => {
  it("setAccessToken сохраняет токен в память и sessionStorage", () => {
    setAccessToken("tok");

    expect(getAccessToken()).toBe("tok");
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe("tok");
  });

  it("clearAccessToken очищает память и sessionStorage", () => {
    setAccessToken("tok");

    clearAccessToken();

    expect(getAccessToken()).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("setAccessToken уведомляет подписчиков новым токеном", () => {
    const listener = vi.fn();
    const off = subscribeAccessToken(listener);

    setAccessToken("tok");

    expect(listener).toHaveBeenCalledWith("tok");
    off();
  });

  it("clearAccessToken уведомляет подписчиков значением null", () => {
    const listener = vi.fn();
    const off = subscribeAccessToken(listener);

    clearAccessToken();

    expect(listener).toHaveBeenCalledWith(null);
    off();
  });

  it("отписанный слушатель не получает обновлений", () => {
    const listener = vi.fn();
    const off = subscribeAccessToken(listener);

    off();
    setAccessToken("tok");

    expect(listener).not.toHaveBeenCalled();
  });

  it("держит токен в памяти, даже если запись в sessionStorage упала", () => {
    breakStorage("setItem");

    expect(() => setAccessToken("tok")).not.toThrow();
    expect(getAccessToken()).toBe("tok");
  });

  it("при инициализации читает токен из sessionStorage", async () => {
    sessionStorage.setItem(STORAGE_KEY, "persisted");
    vi.resetModules();

    const freshModule = await import("./tokenStore");

    expect(freshModule.getAccessToken()).toBe("persisted");
  });

  it("при инициализации возвращает null, если sessionStorage бросает", async () => {
    breakStorage("getItem");
    vi.resetModules();

    const freshModule = await import("./tokenStore");

    expect(freshModule.getAccessToken()).toBeNull();
  });
});
