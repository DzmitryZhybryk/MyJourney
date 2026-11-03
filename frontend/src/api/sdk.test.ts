import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearAccessToken, setAccessToken } from "../auth/tokenStore";
import { jsonResponse, type FetchSignature } from "../test/fetchStub";
import { ApiError } from "./errors";
import { createJourney, getCurrentUser } from "./sdk";

const REFRESH_PATH = "/v1/auth/refresh/";

const JOURNEY_BODY = {
  originCityId: "11111111-1111-4111-8111-111111111111",
  destinationCityId: "22222222-2222-4222-8222-222222222222",
  transportType: "air",
  traveledYear: 2020,
} as const;

let fetchMock: ReturnType<typeof vi.fn<FetchSignature>>;

/** The n-th request the `fetch` stub received (the SDK always sends a `Request`). */
function requestAt(index: number): Request {
  return fetchMock.mock.calls[index][0] as Request;
}

beforeEach(() => {
  clearAccessToken();
  fetchMock = vi.fn<FetchSignature>();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/*
 * The seam between the generated SDK and our transport: the SDK itself is not ours to cover (it is
 * generated), but `sdk.ts` is our code and decides whether a request reaches `appFetch` at all.
 * The whole seam is checked, from an operation call to the resend after refresh.
 */
describe("sdk", () => {
  it("шлёт запрос через транспорт приложения: Bearer, credentials, абсолютный URL", async () => {
    setAccessToken("my-token");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { displayName: "traveler" }));

    await getCurrentUser({ throwOnError: true });

    const request = requestAt(0);
    // baseUrl is required: without it the client would build a relative URL, which `Request` does
    // not resolve outside a browser.
    expect(new URL(request.url).pathname).toBe("/v1/users/me/");
    expect(request.headers.get("Authorization")).toBe("Bearer my-token");
    expect(request.credentials).toBe("include");
  });

  it("POST после протухшего токена повторяется с телом, а не пустым", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { code: "auth.invalid_access_token", message: "x" }))
      .mockResolvedValueOnce(jsonResponse(200, { accessToken: "new-token" }))
      .mockResolvedValueOnce(new Response(null, { status: 201 }));

    await createJourney({ body: JOURNEY_BODY, throwOnError: true });

    expect(fetchMock.mock.calls.filter(([url]) => url === REFRESH_PATH)).toHaveLength(1);
    const retried = requestAt(2);
    expect(retried.method).toBe("POST");
    expect(await retried.json()).toEqual(JOURNEY_BODY);
  });

  it("неуспех доезжает до вызывающего как ApiError с машинным кодом", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(400, { code: "journeys.date_in_future", message: "ru" }));

    await expect(createJourney({ body: JOURNEY_BODY, throwOnError: true })).rejects.toMatchObject({
      status: 400,
      code: "journeys.date_in_future",
    });
  });

  it("ответ не по контракту — invalid_response, а не голый ZodError", async () => {
    // A success status but the body fails the generated zod schema: without the error interceptor a
    // ZodError would escape past applyApiError and the whole error i18n.
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { displayName: 42 }));

    await expect(getCurrentUser({ throwOnError: true })).rejects.toMatchObject({
      status: 200,
      code: "invalid_response",
    });
  });

  it("сетевой сбой остаётся сетевым, а не подменяется invalid_response", async () => {
    // There is no response at all: the interceptor must pass the error through as is, otherwise a
    // dropped connection would render to the user as "the server sent garbage".
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const error = await getCurrentUser({ throwOnError: true }).catch((err: unknown) => err);

    expect(error).toBeInstanceOf(TypeError);
    expect(error).not.toBeInstanceOf(ApiError);
  });
});
