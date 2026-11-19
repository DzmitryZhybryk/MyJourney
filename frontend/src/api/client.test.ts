import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { on } from "../auth/events";
import { clearAccessToken, getAccessToken, setAccessToken } from "../auth/tokenStore";
import { jsonResponse, type FetchSignature } from "../test/fetchStub";
import { appFetch, ensureRefreshed } from "./client";
import { ApiError } from "./errors";

const REFRESH_PATH = "/v1/auth/refresh/";
// The transport builds a `Request`, which does not resolve a relative path outside a browser, so
// addresses in tests are absolute (in the app `sdk.ts` supplies the baseUrl).
const ORIGIN = "https://app.test";

/** The n-th request the `fetch` stub received. */
function requestAt(mock: ReturnType<typeof vi.fn<FetchSignature>>, index: number): Request {
  return mock.mock.calls[index][0] as Request;
}

/** A controllable promise: keeps a request "in flight" and resolves it by hand. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void } {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

/** Counts how many times exactly `/v1/auth/refresh/` was called. */
function refreshCallCount(mock: ReturnType<typeof vi.fn<FetchSignature>>): number {
  return mock.mock.calls.filter(([url]) => url === REFRESH_PATH).length;
}

let fetchMock: ReturnType<typeof vi.fn<FetchSignature>>;

describe("appFetch", () => {
  beforeEach(() => {
    sessionStorage.clear();
    clearAccessToken();
    fetchMock = vi.fn<FetchSignature>();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("отдаёт успешный ответ как есть — разбор тела на стороне SDK", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { id: 1 }));

    const response = await appFetch(`${ORIGIN}/v1/x/`);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: 1 });
  });

  it("подставляет Authorization и credentials include", async () => {
    setAccessToken("my-token");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}));

    await appFetch(`${ORIGIN}/v1/x/`);

    const request = requestAt(fetchMock, 0);
    expect(request.headers.get("Authorization")).toBe("Bearer my-token");
    expect(request.credentials).toBe("include");
  });

  it("не добавляет Authorization без токена", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}));

    await appFetch(`${ORIGIN}/v1/x/`);

    expect(requestAt(fetchMock, 0).headers.has("Authorization")).toBe(false);
  });

  it("на 401 invalid_credentials не делает refresh и бросает ApiError", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_credentials", message: "x" }));

    await expect(appFetch(`${ORIGIN}/v1/auth/login/`, { method: "POST" })).rejects.toMatchObject({
      status: 401,
      code: "auth.invalid_credentials",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("на прочий 401 делает один refresh и повторяет запрос ВМЕСТЕ С ТЕЛОМ", async () => {
    // A request body is a one-shot stream: without a clone before the first send the retry would go
    // out empty and a POST after an expired token would silently lose its payload.
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_access_token", message: "x" }))
      .mockResolvedValueOnce(jsonResponse(200, { accessToken: "new-token" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    const response = await appFetch(`${ORIGIN}/v1/protected/`, {
      method: "POST",
      body: JSON.stringify({ a: 1 }),
      headers: { "Content-Type": "application/json" },
    });

    expect(await response.json()).toEqual({ ok: true });
    expect(getAccessToken()).toBe("new-token");
    expect(refreshCallCount(fetchMock)).toBe(1);
    const retried = requestAt(fetchMock, 2);
    expect(retried.method).toBe("POST");
    expect(await retried.text()).toBe(JSON.stringify({ a: 1 }));
  });

  it("повтор после refresh уходит с НОВЫМ токеном, а не с протухшим", async () => {
    setAccessToken("stale-token");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_access_token", message: "x" }))
      .mockResolvedValueOnce(jsonResponse(200, { accessToken: "fresh-token" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await appFetch(`${ORIGIN}/v1/protected/`);

    expect(requestAt(fetchMock, 0).headers.get("Authorization")).toBe("Bearer stale-token");
    expect(requestAt(fetchMock, 2).headers.get("Authorization")).toBe("Bearer fresh-token");
  });

  it("если повтор после refresh упал — бросает ошибку повтора", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_access_token", message: "x" }))
      .mockResolvedValueOnce(jsonResponse(200, { accessToken: "new-token" }))
      .mockResolvedValueOnce(jsonResponse(500, { code: "internal_error", message: "x" }));

    await expect(appFetch(`${ORIGIN}/v1/protected/`)).rejects.toMatchObject({
      status: 500,
      code: "internal_error",
    });
  });

  // account_not_found: a valid token whose account is gone ends the session the same way.
  it.each(["auth.invalid_access_token", "auth.account_not_found"])(
    "если refresh после 401 %s не удался — эмитит auth-required и бросает исходную ошибку",
    async (code) => {
      const authListener = vi.fn();
      const off = on("auth-required", authListener);
      fetchMock
        .mockResolvedValueOnce(jsonResponse(401, { code, message: "x" }))
        .mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_refresh_token", message: "x" }));

      const error: unknown = await appFetch(`${ORIGIN}/v1/x/`).catch((reason: unknown) => reason);

      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ status: 401, code });
      expect(authListener).toHaveBeenCalledTimes(1);
      off();
    },
  );

  it("на ошибку без валидного JSON-тела отдаёт unknown_error", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("<html>502</html>", { status: 502, headers: { "Content-Type": "text/html" } }),
    );

    await expect(appFetch(`${ORIGIN}/v1/x/`)).rejects.toMatchObject({ status: 502, code: "unknown_error" });
  });

  it("на 401 самого /refresh/ не уходит в цикл refresh", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_refresh_token", message: "x" }));

    await expect(appFetch(`${ORIGIN}${REFRESH_PATH}`, { method: "POST" })).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("ensureRefreshed", () => {
  beforeEach(() => {
    sessionStorage.clear();
    clearAccessToken();
    fetchMock = vi.fn<FetchSignature>();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("два параллельных вызова делают один запрос /refresh/ (single-flight)", async () => {
    const inFlight = deferred<Response>();
    fetchMock.mockReturnValueOnce(inFlight.promise);

    const first = ensureRefreshed();
    const second = ensureRefreshed();
    inFlight.resolve(jsonResponse(200, { accessToken: "shared" }));
    const [firstResult, secondResult] = await Promise.all([first, second]);

    expect(firstResult).toBe(true);
    expect(secondResult).toBe(true);
    expect(refreshCallCount(fetchMock)).toBe(1);
    expect(getAccessToken()).toBe("shared");
  });

  it("возвращает true и пишет токен при успешном refresh", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { accessToken: "fresh" }));

    expect(await ensureRefreshed()).toBe(true);
    expect(getAccessToken()).toBe("fresh");
  });

  it("возвращает false при неуспешном /refresh/", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_refresh_token", message: "x" }));

    expect(await ensureRefreshed()).toBe(false);
    expect(getAccessToken()).toBeNull();
  });

  it("возвращает false, если запрос упал с исключением", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network down"));

    expect(await ensureRefreshed()).toBe(false);
  });
});
