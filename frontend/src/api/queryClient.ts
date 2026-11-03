import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./errors";

// Three retries after the first attempt: Query backoff is exponential, and by the fourth the
// wait is longer than a user will stare at a spinner.
const MAX_RETRIES = 3;

/**
 * Retry only transient failures: network, 5xx, malformed response. An `ApiError` with 4xx is a
 * real server answer and a retry returns the same thing; a 401 has already had its refresh
 * retry in the transport.
 */
export function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) {
    return false;
  }

  return failureCount < MAX_RETRIES;
}

/**
 * Builds the app's Query client. A factory, not a module singleton: `main.tsx` owns the cache,
 * and each test gets an isolated instance.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry },
    },
  });
}
