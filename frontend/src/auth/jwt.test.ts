import { describe, expect, it } from "vitest";

import { base64Url, makeToken } from "../test/handlers";
import { decodeAccessTokenClaims } from "./jwt";

describe("decodeAccessTokenClaims", () => {
  it("декодирует валидный access-токен в claims, без роли — обычный пользователь", () => {
    const token = makeToken({ sub: "user-1", email_verified: true, exp: 1_700_000_000 });

    expect(decodeAccessTokenClaims(token)).toEqual({
      sub: "user-1",
      email_verified: true,
      exp: 1_700_000_000,
      role: "user",
    });
  });

  it("читает роль из токена", () => {
    const token = makeToken({ sub: "admin-1", email_verified: true, exp: 1_700_000_000, role: "admin" });

    expect(decodeAccessTokenClaims(token)?.role).toBe("admin");
  });

  it("возвращает null для токена не из трёх частей", () => {
    expect(decodeAccessTokenClaims("only.two")).toBeNull();
  });

  it("возвращает null при битом base64 в payload", () => {
    expect(decodeAccessTokenClaims("header.@@@.signature")).toBeNull();
  });

  it("возвращает null, если payload не JSON", () => {
    const token = `header.${base64Url("not json{")}.signature`;

    expect(decodeAccessTokenClaims(token)).toBeNull();
  });

  it("возвращает null при несоответствии схеме (нет email_verified)", () => {
    const token = makeToken({ sub: "user-1", exp: 1_700_000_000 });

    expect(decodeAccessTokenClaims(token)).toBeNull();
  });

  it("возвращает null, если sub не строка", () => {
    const token = makeToken({ sub: 123, email_verified: true, exp: 1_700_000_000 });

    expect(decodeAccessTokenClaims(token)).toBeNull();
  });
});
