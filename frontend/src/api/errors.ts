import { i18n } from "../i18n";

export type ApiErrorBody = {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  timestamp?: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? null;
  }
}

type FormLike = {
  setFieldError: (path: string, error: string) => void;
};

/** Interpolation values for an error text, e.g. `{ minutes: 9 }` for `{{minutes}}`. */
export type ErrorParams = Readonly<Record<string, number>>;

/**
 * Prefix of an i18n token for a backend error code (`errors` namespace).
 *
 * Error tokens are stored as strings and resolved to text at render time, not when the error
 * happens, so a language switch updates a message that is already on screen. The prefix tells a
 * backend code (`errors:auth.invalid_credentials`) from a frontend validation key
 * (`auth:validation.usernameMin`) in the single resolver.
 */
const ERROR_CODE_PREFIX = "errors:";

/** Wraps a backend error code (or `"network"`) into an `errors:<code>` token for `resolveErrorToken`. */
export function errorCodeToken(code: string): string {
  return `${ERROR_CODE_PREFIX}${code}`;
}

/**
 * Resolves a stored error token to text in the active language; `undefined` for an empty or
 * non-string token. The token is either a backend code (`errors:<code>`) or a namespaced
 * frontend validation key. Call it on every render; `params` fill the text's placeholders.
 */
export function resolveErrorToken(token: unknown, params?: ErrorParams): string | undefined {
  if (typeof token !== "string" || token.length === 0) {
    return undefined;
  }

  if (token.startsWith(ERROR_CODE_PREFIX)) {
    return messageForCode(token.slice(ERROR_CODE_PREFIX.length), undefined, params);
  }

  return i18n.t(token, params);
}

/**
 * Resolves the `error` token inside input props from `form.getInputProps` at render time, so the
 * message follows a language switch. Other props pass through unchanged.
 */
export function withLocalizedError<T extends { error?: unknown }>(
  props: T,
): Omit<T, "error"> & { error: string | undefined } {
  return { ...props, error: resolveErrorToken(props.error) };
}

/**
 * User-facing message for a backend error code, from the `errors` namespace. The backend
 * `message` is never shown. An unknown code resolves to `fallback` (default `errors:fallback`).
 */
export function messageForCode(code: string, fallback?: string, params?: ErrorParams): string {
  const resolvedFallback = fallback ?? i18n.t("fallback", { ns: "errors" });
  return i18n.t(code, { ...params, ns: "errors", defaultValue: resolvedFallback });
}

function snakeToCamel(value: string): string {
  return value.replace(/_([a-z])/gu, (_, ch: string) => ch.toUpperCase());
}

/**
 * Applies an API error to the given form when possible, returns a top-level
 * error token otherwise.
 *
 * Field-bound errors arrive from the backend with `details.field` (snake_case).
 * They are converted to camelCase to match RHF/Mantine form field names and
 * pushed via `form.setFieldError`. Anything else (no details, non-ApiError,
 * unknown shape) becomes a top-level token.
 *
 * Returns an **error token** (`errors:<code>`), not resolved text: the caller
 * stores it and resolves it at render via `resolveErrorToken`, so the message
 * follows a language switch. The text is always derived from the machine `code`,
 * never from the backend `message` (which is in Russian and may not match the
 * UI language).
 */
export function applyApiError(err: unknown, form: FormLike): string | null {
  if (!(err instanceof ApiError)) {
    return errorCodeToken("network");
  }

  const rawField = err.details?.field;
  if (typeof rawField === "string" && rawField.length > 0) {
    form.setFieldError(snakeToCamel(rawField), errorCodeToken(err.code));
    return null;
  }

  return errorCodeToken(err.code);
}
