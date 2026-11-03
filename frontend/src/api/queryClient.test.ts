import { describe, expect, it } from "vitest";

import { ApiError } from "./errors";
import { createQueryClient, shouldRetry } from "./queryClient";

/** An `ApiError` with the given status; code and text do not matter for the retry policy. */
function apiError(status: number): ApiError {
  return new ApiError(status, { code: "any_code", message: "any" });
}

describe("shouldRetry", () => {
  it.each([400, 401, 403, 404, 409, 422, 429])("не повторяет ApiError со статусом %i", (status) => {
    expect(shouldRetry(0, apiError(status))).toBe(false);
  });

  it("не повторяет invalid_response — битое тело придёт таким же", () => {
    // The transport returns it with a success status, so the "status < 500" check must catch this
    // case too, not only 4xx.
    expect(shouldRetry(0, new ApiError(200, { code: "invalid_response", message: "broken" }))).toBe(false);
  });

  it.each([500, 502, 503])("повторяет ApiError со статусом %i", (status) => {
    expect(shouldRetry(0, apiError(status))).toBe(true);
  });

  it("повторяет сетевую ошибку (не ApiError)", () => {
    expect(shouldRetry(0, new TypeError("Failed to fetch"))).toBe(true);
  });

  it("перестаёт повторять после трёх неудач", () => {
    expect(shouldRetry(2, apiError(500))).toBe(true);
    expect(shouldRetry(3, apiError(500))).toBe(false);
  });
});

describe("createQueryClient", () => {
  it("ставит политику повторов дефолтом для запросов", () => {
    const retry = createQueryClient().getDefaultOptions().queries?.retry;

    expect(retry).toBe(shouldRetry);
  });

  it("отдаёт новый клиент на каждый вызов — кэш не общий", () => {
    expect(createQueryClient()).not.toBe(createQueryClient());
  });
});
