import { describe, expect, it } from "vitest";

import { readAccountsSearch, toListAccountsQuery, writeAccountsSearch } from "./accountsSearch";

describe("accountsSearch", () => {
  it("без параметров — первая страница без фильтров, сначала новые", () => {
    expect(readAccountsSearch(new URLSearchParams())).toEqual({
      page: 1,
      email: "",
      displayName: "",
      role: "",
      consent: "any",
      includeDeleted: false,
      sortDirection: "desc",
    });
  });

  it("читает каждый параметр в своё поле и пишет обратно те же параметры", () => {
    const params = new URLSearchParams("page=3&email=neo&name=Ne&role=admin&consent=no&deleted=1&sort=asc");

    const search = readAccountsSearch(params);

    expect(search).toEqual({
      page: 3,
      email: "neo",
      displayName: "Ne",
      role: "admin",
      consent: "no",
      includeDeleted: true,
      sortDirection: "asc",
    });
    expect(writeAccountsSearch(search).toString()).toBe(params.toString());
  });

  it("испорченные значения сводит к безопасным, а номер страницы — к границе бэкенда", () => {
    const search = readAccountsSearch(
      new URLSearchParams(`page=-2&consent=maybe&deleted=yes&sort=sideways&email=${"a".repeat(300)}`),
    );

    expect(search.page).toBe(1);
    expect(search.consent).toBe("any");
    expect(search.includeDeleted).toBe(false);
    expect(search.sortDirection).toBe("desc");
    expect(search.email).toHaveLength(254);
    expect(readAccountsSearch(new URLSearchParams("page=99999")).page).toBe(10_000);
    expect(readAccountsSearch(new URLSearchParams("page=2.5")).page).toBe(1);
  });

  it("значения по умолчанию в адрес не попадают", () => {
    expect(writeAccountsSearch(readAccountsSearch(new URLSearchParams("page=1&sort=desc&consent=any"))).toString()).toBe(
      "",
    );
  });

  it("в запрос уходят только заданные фильтры, согласие — булевым, размер страницы — явно", () => {
    expect(toListAccountsQuery(readAccountsSearch(new URLSearchParams("consent=yes")))).toEqual({
      page: 1,
      limit: 20,
      email: undefined,
      displayName: undefined,
      role: undefined,
      marketingEmailsConsent: true,
      includeDeleted: false,
      sortDirection: "desc",
    });
  });
});
