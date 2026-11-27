import { Button, Loader, Pagination, Text } from "@mantine/core";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { listAccountsOptions } from "../../api/sdk";
import { AccountsFilters } from "./AccountsFilters";
import { AccountsTable } from "./AccountsTable";
import {
  hasFilters,
  NO_FILTERS,
  PAGE_SIZE,
  readAccountsSearch,
  toListAccountsQuery,
  writeAccountsSearch,
  type AccountsFilters as Filters,
  type AccountsSearch,
} from "./accountsSearch";
import "./accounts.css";

/**
 * Every account as the admin sees it, filtered and paged. The page, the filters and the sort
 * direction live in the URL, so a link or a reload opens the same list; a filter change goes back
 * to page 1.
 */
export function AccountsPage() {
  const { t } = useTranslation("admin");
  const [params, setParams] = useSearchParams();
  const search = readAccountsSearch(params);
  const isFiltered = hasFilters(search);
  // The previous page stays on screen while the next one loads, instead of the table blinking out.
  const accounts = useQuery({
    ...listAccountsOptions({ query: toListAccountsQuery(search) }),
    placeholderData: keepPreviousData,
  });

  const navigate = (next: AccountsSearch, { replace }: { replace: boolean }) => {
    const nextParams = writeAccountsSearch(next);
    if (nextParams.toString() === writeAccountsSearch(search).toString()) return;
    setParams(nextParams, { replace });
  };

  // Typing must not leave one history entry per pause; paging and sorting are steps worth going back to.
  const changeFilters = (patch: Partial<Filters>) => navigate({ ...search, ...patch, page: 1 }, { replace: true });
  const changePage = (page: number) => navigate({ ...search, page }, { replace: false });
  const toggleSort = () =>
    navigate(
      { ...search, page: 1, sortDirection: search.sortDirection === "desc" ? "asc" : "desc" },
      { replace: false },
    );

  const data = accounts.data;
  const pageCount = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const firstRow = (search.page - 1) * PAGE_SIZE + 1;

  return (
    <section className="accounts-card" aria-labelledby="accounts-title">
      <header className="accounts-card__header">
        <h1 id="accounts-title" className="accounts-card__title">
          {t("sections.accounts")}
        </h1>
        {data && data.items.length > 0 && (
          <span className="accounts-card__range">
            {t("accounts.range", { from: firstRow, to: firstRow + data.items.length - 1, total: data.total })}
          </span>
        )}
      </header>

      <AccountsFilters filters={search} hasFilters={isFiltered} onChange={changeFilters} />

      {accounts.isError && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="md">
          {t("accounts.loadError")}
        </Text>
      )}
      {accounts.isPending && <Loader className="accounts-card__loader" />}

      {data && data.items.length > 0 && (
        <AccountsTable
          accounts={data.items}
          sortDirection={search.sortDirection}
          isStale={accounts.isPlaceholderData}
          onToggleSort={toggleSort}
        />
      )}

      {data && data.items.length === 0 && (
        <div className="accounts-card__empty">
          {data.total > 0 ? (
            <>
              <p>{t("accounts.pageEmpty")}</p>
              <Button variant="default" onClick={() => changePage(1)}>
                {t("accounts.toFirstPage")}
              </Button>
            </>
          ) : (
            <>
              <p>{isFiltered ? t("accounts.empty") : t("accounts.emptyAll")}</p>
              {isFiltered && (
                <Button variant="default" onClick={() => changeFilters(NO_FILTERS)}>
                  {t("accounts.filters.reset")}
                </Button>
              )}
            </>
          )}
        </div>
      )}

      {pageCount > 1 && (
        <nav className="accounts-card__pages" aria-label={t("accounts.pagination")}>
          <Pagination total={pageCount} value={Math.min(search.page, pageCount)} onChange={changePage} />
        </nav>
      )}
    </section>
  );
}
