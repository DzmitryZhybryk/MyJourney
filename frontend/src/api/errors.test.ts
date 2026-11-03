import { describe, expect, it, vi } from "vitest";

import {
  ApiError,
  applyApiError,
  errorCodeToken,
  messageForCode,
  resolveErrorToken,
  withLocalizedError,
} from "./errors";

describe("messageForCode", () => {
  it("возвращает локализованный текст для известного кода", () => {
    expect(messageForCode("auth.invalid_credentials")).toBe("Incorrect username/email or password");
  });

  it("возвращает дефолтный fallback для неизвестного кода", () => {
    expect(messageForCode("totally.unknown")).toBe("Something went wrong. Please try again.");
  });

  it("использует переданный fallback для неизвестного кода", () => {
    expect(messageForCode("totally.unknown", "Custom fallback")).toBe("Custom fallback");
  });
});

describe("resolveErrorToken", () => {
  it("резолвит токен кода бэка в локализованный текст", () => {
    expect(resolveErrorToken(errorCodeToken("auth.invalid_credentials"))).toBe(
      "Incorrect username/email or password",
    );
  });

  it("резолвит неизвестный код в fallback", () => {
    expect(resolveErrorToken(errorCodeToken("totally.unknown"))).toBe(
      "Something went wrong. Please try again.",
    );
  });

  it("подставляет параметры в текст кода бэка", () => {
    expect(
      resolveErrorToken(errorCodeToken("auth.challenge_attempts_exceeded_retry"), { minutes: 9 }),
    ).toBe("Too many attempts. You can request a new code in 9 min");
  });

  it("резолвит токен валидации из namespace auth", () => {
    expect(resolveErrorToken("auth:validation.usernameMin")).toBe(
      "Username must be at least 3 characters",
    );
  });

  it("резолвит токен валидации из namespace journeys", () => {
    expect(resolveErrorToken("journeys:addJourney.validation.originRequired")).toBe(
      "Choose the departure city",
    );
  });

  it("возвращает undefined для отсутствующего токена", () => {
    expect(resolveErrorToken(undefined)).toBeUndefined();
    expect(resolveErrorToken(null)).toBeUndefined();
    expect(resolveErrorToken("")).toBeUndefined();
  });
});

describe("withLocalizedError", () => {
  it("резолвит error в пропсах и пропускает остальные поля без изменений", () => {
    const onChange = vi.fn();
    const inputProps = { error: "auth:validation.usernameMin", value: "ab", onChange };

    const props = withLocalizedError(inputProps);

    expect(props).toStrictEqual({
      error: "Username must be at least 3 characters",
      value: "ab",
      onChange,
    });
  });

  it("ставит error в undefined, когда токена ошибки нет", () => {
    const inputProps = { value: "ok", error: undefined };

    const props = withLocalizedError(inputProps);

    expect(props.error).toBeUndefined();
  });
});

describe("applyApiError", () => {
  it("для не-ApiError возвращает network-токен и не трогает форму", () => {
    const form = { setFieldError: vi.fn() };

    const token = applyApiError(new Error("boom"), form);

    expect(token).toBe(errorCodeToken("network"));
    expect(resolveErrorToken(token)).toBe("Network error. Please try again.");
    expect(form.setFieldError).not.toHaveBeenCalled();
  });

  it("привязывает токен к полю с конверсией snake_case → camelCase", () => {
    const form = { setFieldError: vi.fn() };
    const err = new ApiError(409, {
      code: "auth.username_already_taken",
      message: "русский текст бэка",
      details: { field: "user_name" },
    });

    const token = applyApiError(err, form);

    expect(token).toBeNull();
    expect(form.setFieldError).toHaveBeenCalledWith(
      "userName",
      errorCodeToken("auth.username_already_taken"),
    );
    expect(resolveErrorToken(errorCodeToken("auth.username_already_taken"))).toBe(
      "This username is already taken",
    );
  });

  it("без поля в details возвращает токен верхнего уровня", () => {
    const form = { setFieldError: vi.fn() };
    const err = new ApiError(401, { code: "auth.invalid_credentials", message: "русский текст бэка" });

    const token = applyApiError(err, form);

    expect(token).toBe(errorCodeToken("auth.invalid_credentials"));
    expect(resolveErrorToken(token)).toBe("Incorrect username/email or password");
    expect(form.setFieldError).not.toHaveBeenCalled();
  });
});
