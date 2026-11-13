import { emit } from "../auth/events";
import { getAccessToken, setAccessToken } from "../auth/tokenStore";
import { ApiError, type ApiErrorBody } from "./errors";

const INVALID_CREDENTIALS_CODE = "auth.invalid_credentials";
const REFRESH_PATH = "/v1/auth/refresh/";

let pendingRefresh: Promise<boolean> | null = null;

function shouldRetryAfterRefresh(status: number, code: string, pathname: string): boolean {
  return status === 401 && code !== INVALID_CREDENTIALS_CODE && pathname !== REFRESH_PATH;
}

/**
 * Transport of the generated SDK: the only path for every call to our API.
 *
 * The SDK parses and validates successful responses; this handles the session and failures:
 * Bearer from `tokenStore`, refresh cookie, single-flight refresh on 401 with a retry, and the
 * `auth-required` event. Throws `ApiError` on non-2xx.
 */
export async function appFetch(input: URL | RequestInfo, init?: RequestInit): Promise<Response> {
  const request = new Request(input, init);

  // A request body is a one-shot stream, so clone for the retry before the first send.
  const retryable = request.clone();
  const { pathname } = new URL(request.url);

  const response = await sendWithSession(request);
  if (response.ok) {
    return response;
  }

  const errorBody = await parseErrorBody(response);

  if (shouldRetryAfterRefresh(response.status, errorBody.code, pathname)) {
    const refreshed = await ensureRefreshed();
    if (refreshed) {
      const retryResponse = await sendWithSession(retryable);
      if (retryResponse.ok) {
        return retryResponse;
      }

      throw new ApiError(retryResponse.status, await parseErrorBody(retryResponse));
    }

    emit("auth-required", undefined);
  }

  throw new ApiError(response.status, errorBody);
}

function sendWithSession(request: Request): Promise<Response> {
  const headers = withAuthorization(new Headers(request.headers));

  return fetch(new Request(request, { credentials: "include", headers }));
}

/**
 * Calls `/refresh/` bypassing the SDK: `sdk.ts` configures the client with this transport, so
 * importing the generated `refresh()` here would create an import cycle.
 *
 * The path is a string, not a `Request`: outside a browser (jsdom + undici) a relative URL in
 * the `Request` constructor fails with "Failed to parse URL".
 */
function sendRefreshRequest(): Promise<Response> {
  return fetch(REFRESH_PATH, {
    method: "POST",
    credentials: "include",
    headers: withAuthorization(new Headers()),
  });
}

function withAuthorization(headers: Headers): Headers {
  const token = getAccessToken();
  if (token !== null && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return headers;
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody> {
  const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
  return body ?? { code: "unknown_error", message: "Unexpected server response" };
}

/**
 * Single-flight refresh: concurrent callers share one pending promise. Covers both refresh
 * sources: 401 retries from `appFetch` and the `AuthContext` bootstrap (including the double
 * effect run under StrictMode). Critical because the backend rotates refresh tokens with
 * reuse detection: two parallel `/refresh/` calls with one cookie would revoke the whole session.
 *
 * Resolves `true` if a valid session exists (access token stored in `tokenStore`).
 */
export function ensureRefreshed(): Promise<boolean> {
  if (pendingRefresh !== null) {
    return pendingRefresh;
  }

  pendingRefresh = (async () => {
    try {
      const response = await sendRefreshRequest();
      if (!response.ok) {
        return false;
      }

      const body = (await response.json()) as { accessToken: string };
      setAccessToken(body.accessToken);
      return true;
    } catch {
      return false;
    } finally {
      pendingRefresh = null;
    }
  })();

  return pendingRefresh;
}
