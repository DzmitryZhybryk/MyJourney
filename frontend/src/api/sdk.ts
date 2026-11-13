/**
 * The only entry point to the generated SDK.
 *
 * Never import from `./generated` directly: the client is configured here, and bypassing this
 * module would send bare `fetch` calls without Bearer, refresh cookie or single-flight refresh.
 */
import { appFetch } from "./client";
import { ApiError } from "./errors";
import { client } from "./generated/client.gen";

// baseUrl is required: the client builds the Request itself, and outside a browser (jsdom + undici
// in tests) a relative URL cannot be resolved ("Failed to parse URL"). The API is on the same origin.
// throwOnError is required too: the client catches any transport throw and, without the flag,
// returns the ApiError as a result instead of throwing. Call sites repeat it to narrow the type.
client.setConfig({ baseUrl: window.location.origin, fetch: appFetch, throwOnError: true });

// The transport already turns error responses into ApiError. Anything else the client throws is a
// failure to parse a successful response (bad JSON, zod validation): without this seam a
// SyntaxError or ZodError would bypass applyApiError and the error i18n.
client.interceptors.error.use((error, response) => {
  // No response means a network failure or abort; applyApiError reports it as network, leave it.
  if (error instanceof ApiError || !response) {
    return error;
  }

  return new ApiError(response.status, { code: "invalid_response", message: "Malformed response body" });
});

export * from "./generated";
export * from "./generated/@tanstack/react-query.gen";
export * from "./generated/zod.gen";
