import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { AdminAccountsListResponse } from "../../api/sdk";
import { server, TEST_ACCOUNTS_PAGE } from "../../test/handlers";
import { makeAuthValue, renderWithProviders, screen, waitFor, within } from "../../test/render";
import { AccountsPage } from "./AccountsPage";

const ACCOUNTS_PATH = "/v1/admin/backoffice/accounts/";

function renderPage(route = "/admin/accounts") {
  return renderWithProviders(<AccountsPage />, {
    route,
    authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
  });
}

/** Serves `page` and records the query of every list request, in order. */
function serveAccounts(page: AdminAccountsListResponse = TEST_ACCOUNTS_PAGE): URLSearchParams[] {
  const queries: URLSearchParams[] = [];
  server.use(
    http.get(ACCOUNTS_PATH, ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      return HttpResponse.json(page);
    }),
  );
  return queries;
}

describe("AccountsPage", () => {
  it("показывает строки с подписями роли и тарифа, счётчик и пометку удалённого", async () => {
    renderPage();

    const table = await screen.findByRole("table");
    const neoRow = within(table).getByRole("row", { name: /neo@example\.com/u });

    expect(within(neoRow).getByText("@neo")).toBeInTheDocument();
    expect(within(neoRow).getByText("Administrator")).toBeInTheDocument();
    expect(within(neoRow).getByText("Premium")).toBeInTheDocument();
    expect(within(neoRow).getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText("1–2 of 2")).toBeInTheDocument();
    expect(within(table).getByText("deleted 11/21/26")).toBeInTheDocument();
  });

  it("пустые части строки показывает прочерком, а незнакомую роль — как есть", async () => {
    serveAccounts({
      items: [{ ...TEST_ACCOUNTS_PAGE.items[1], role: "moderator", deletedAt: null }],
      total: 1,
    });
    renderPage();

    const row = await screen.findByRole("row", { name: /smith@example\.com/u });

    expect(within(row).getByText("moderator")).toBeInTheDocument();
    expect(within(row).getAllByText("—")).toHaveLength(4);
  });

  it("открывает список с фильтрами, страницей и порядком из адреса", async () => {
    const queries = serveAccounts();
    renderPage("/admin/accounts?page=2&email=neo&role=admin&consent=no&deleted=1&sort=asc");

    await waitFor(() => expect(queries).toHaveLength(1));

    expect(Object.fromEntries(queries[0])).toEqual({
      page: "2",
      limit: "20",
      email: "neo",
      role: "admin",
      marketingEmailsConsent: "false",
      includeDeleted: "true",
      sortDirection: "asc",
    });
    expect(screen.getByRole("textbox", { name: "Email" })).toHaveValue("neo");
    expect(screen.getByRole("switch", { name: "Show deleted" })).toBeChecked();
    expect(screen.getByPlaceholderText("All")).toHaveValue("No");
  });

  it("рассылки выбираются из списка, а сброс возвращает «все»", async () => {
    const queries = serveAccounts();
    const { user } = renderPage();
    await screen.findByRole("table");

    await user.click(screen.getByPlaceholderText("All"));
    await user.click(await screen.findByRole("option", { name: "Yes", hidden: true }));

    await waitFor(() => expect(queries.at(-1)?.get("marketingEmailsConsent")).toBe("true"));

    await user.click(screen.getByRole("button", { name: "Reset filters" }));

    await waitFor(() => expect(queries.at(-1)?.has("marketingEmailsConsent")).toBe(false));
    expect(screen.getByPlaceholderText("All")).toHaveValue("");
  });

  it("фильтр по email уходит после паузы в наборе и возвращает на первую страницу", async () => {
    const queries = serveAccounts();
    const { user } = renderPage("/admin/accounts?page=3");
    await waitFor(() => expect(queries).toHaveLength(1));

    await user.type(screen.getByRole("textbox", { name: "Email" }), "neo");

    await waitFor(() => expect(queries.at(-1)?.get("email")).toBe("neo"));
    expect(queries.at(-1)?.get("page")).toBe("1");
    expect(queries.filter((query) => query.has("email"))).toHaveLength(1);
  });

  it("роль из списка, который отдаёт auth, сужает выдачу", async () => {
    const queries = serveAccounts();
    const { user } = renderPage();
    await screen.findByRole("table");

    await user.click(screen.getByPlaceholderText("All roles"));
    await user.click(await screen.findByRole("option", { name: "Administrator", hidden: true }));

    await waitFor(() => expect(queries.at(-1)?.get("role")).toBe("admin"));
  });

  it("клик по заголовку «Registered» разворачивает порядок и возвращает на первую страницу", async () => {
    const queries = serveAccounts();
    const { user } = renderPage("/admin/accounts?page=2");
    const header = await screen.findByRole("columnheader", { name: /Registered/u });

    expect(header).toHaveAttribute("aria-sort", "descending");

    await user.click(within(header).getByRole("button", { name: /Registered/u }));

    await waitFor(() => expect(queries.at(-1)?.get("sortDirection")).toBe("asc"));
    expect(queries.at(-1)?.get("page")).toBe("1");
    expect(await screen.findByRole("columnheader", { name: /Registered/u })).toHaveAttribute("aria-sort", "ascending");
  });

  it("номер страницы в пагинации запрашивает эту страницу", async () => {
    const queries = serveAccounts({ items: TEST_ACCOUNTS_PAGE.items, total: 45 });
    const { user } = renderPage();
    const pages = await screen.findByRole("navigation", { name: "Account list pages" });

    await user.click(within(pages).getByRole("button", { name: "2" }));

    await waitFor(() => expect(queries.at(-1)?.get("page")).toBe("2"));
  });

  it("пустая выдача под фильтром предлагает сбросить фильтры", async () => {
    const queries = serveAccounts({ items: [], total: 0 });
    const { user } = renderPage("/admin/accounts?email=nobody&consent=yes");

    expect(await screen.findByText("No accounts match the filters.")).toBeInTheDocument();

    const [, resetInEmptyState] = screen.getAllByRole("button", { name: "Reset filters" });
    await user.click(resetInEmptyState);

    await waitFor(() => expect(queries.at(-1)?.toString()).toBe("page=1&limit=20&includeDeleted=false&sortDirection=desc"));
    expect(screen.getByRole("textbox", { name: "Email" })).toHaveValue("");
  });

  it("пустая выдача без фильтров говорит, что аккаунтов пока нет", async () => {
    serveAccounts({ items: [], total: 0 });
    renderPage();

    expect(await screen.findByText("No accounts yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset filters" })).not.toBeInTheDocument();
  });

  it("страница за концом списка предлагает перейти к первой", async () => {
    const queries = serveAccounts({ items: [], total: 3 });
    const { user } = renderPage("/admin/accounts?page=9");

    await user.click(await screen.findByRole("button", { name: "Go to the first page" }));

    await waitFor(() => expect(queries.at(-1)?.get("page")).toBe("1"));
  });

  it("ошибка загрузки показывает сообщение вместо таблицы", async () => {
    server.use(http.get(ACCOUNTS_PATH, () => HttpResponse.json({ code: "internal_error" }, { status: 500 })));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't load the accounts. Reload the page.");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
