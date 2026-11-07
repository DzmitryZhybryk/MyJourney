import { ApiError } from "../api/errors";

// Codes meaning there is no live user: retrying is pointless and the session must be logged out.
// Branch on `code` (the stable API contract), not the HTTP status (a transport detail).
const SESSION_INVALID_CODES: ReadonlySet<string> = new Set(["users.user_deleted", "users.user_not_found"]);

export function isSessionInvalid(error: unknown): boolean {
  return error instanceof ApiError && SESSION_INVALID_CODES.has(error.code);
}
