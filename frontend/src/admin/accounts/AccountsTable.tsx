import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import type { AccountListEntry, SortDirectionEnum } from "../../api/sdk";
import { labelKeyOf, PLAN_LABEL_KEYS, ROLE_LABEL_KEYS } from "./accountLabels";

const EMPTY_CELL = "—";

interface AccountsTableProps {
  accounts: readonly AccountListEntry[];
  sortDirection: SortDirectionEnum;
  isStale: boolean;
  onToggleSort: () => void;
}

/**
 * One page of accounts. The read model fills in from two domains independently, so any value but
 * the id may be missing and shows as a dash.
 */
export function AccountsTable({ accounts, sortDirection, isStale, onToggleSort }: AccountsTableProps) {
  const { t } = useTranslation("admin");
  const formatDate = useDateFormat();
  const sortArrow = sortDirection === "desc" ? "↓" : "↑";

  const label = (labelKeys: Readonly<Record<string, string>>, value: string | null) => {
    if (value === null) return EMPTY_CELL;
    const key = labelKeyOf(labelKeys, value);
    return key === null ? value : t(key);
  };

  const consent = (value: boolean | null) => {
    if (value === null) return EMPTY_CELL;
    return value ? t("accounts.consent.yes") : t("accounts.consent.no");
  };

  return (
    <div className="accounts-table-wrap">
      <table className={isStale ? "accounts-table accounts-table--stale" : "accounts-table"} aria-busy={isStale}>
        <thead>
          <tr>
            <th scope="col">{t("accounts.columns.account")}</th>
            <th scope="col">{t("accounts.columns.name")}</th>
            <th scope="col">{t("accounts.columns.role")}</th>
            <th scope="col">{t("accounts.columns.plan")}</th>
            <th scope="col">{t("accounts.columns.emailVerified")}</th>
            <th scope="col">{t("accounts.columns.consent")}</th>
            <th scope="col">{t("accounts.columns.terms")}</th>
            <th scope="col" aria-sort={sortDirection === "desc" ? "descending" : "ascending"}>
              <button
                type="button"
                className="accounts-table__sort"
                onClick={onToggleSort}
                title={t(`accounts.sort.${sortDirection}`)}
              >
                {t("accounts.columns.registered")}
                <span aria-hidden="true">{sortArrow}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.userId} className={account.deletedAt === null ? undefined : "accounts-row--deleted"}>
              <td>
                <span className="accounts-row__email" title={account.userId}>
                  {account.email ?? EMPTY_CELL}
                </span>
                {(account.username !== null || account.deletedAt !== null) && (
                  <span className="accounts-row__sub">
                    {account.username !== null && <span>@{account.username}</span>}
                    {account.deletedAt !== null && (
                      <span className="accounts-row__deleted">
                        {t("accounts.deleted", { date: formatDate(account.deletedAt).short })}
                      </span>
                    )}
                  </span>
                )}
              </td>
              <td>{account.displayName ?? EMPTY_CELL}</td>
              <td>{label(ROLE_LABEL_KEYS, account.role)}</td>
              <td>{label(PLAN_LABEL_KEYS, account.plan)}</td>
              <td>
                <DateCell value={account.emailVerifiedAt} formatDate={formatDate} />
              </td>
              <td>{consent(account.marketingEmailsConsent)}</td>
              <td>
                <DateCell value={account.termsAcceptedAt} formatDate={formatDate} />
              </td>
              <td>
                <DateCell value={account.registeredAt} formatDate={formatDate} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface FormattedDate {
  short: string;
  full: string;
}

type DateFormat = (iso: string) => FormattedDate;

function useDateFormat(): DateFormat {
  const { i18n } = useTranslation();
  return useMemo(() => {
    const short = new Intl.DateTimeFormat(i18n.language, { dateStyle: "short" });
    const full = new Intl.DateTimeFormat(i18n.language, { dateStyle: "long", timeStyle: "short" });
    return (iso) => {
      const date = new Date(iso);
      return { short: short.format(date), full: full.format(date) };
    };
  }, [i18n.language]);
}

interface DateCellProps {
  value: string | null;
  formatDate: DateFormat;
}

function DateCell({ value, formatDate }: DateCellProps) {
  if (value === null) return EMPTY_CELL;
  const date = formatDate(value);
  return (
    <time dateTime={value} title={date.full}>
      {date.short}
    </time>
  );
}
