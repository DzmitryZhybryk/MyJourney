import { useTranslation } from "react-i18next";

import type { AccountLookupResult } from "./useAccountsByIds";

interface AccountLabelProps {
  accountId: string;
  account: AccountLookupResult;
}

/** An account on an admin screen: its email, a deleted mark, or the raw id until auth answers. */
export function AccountLabel({ accountId, account }: AccountLabelProps) {
  const { t } = useTranslation("admin");

  let label = accountId;
  if (account === null) {
    label = t("account.missing");
  } else if (account !== undefined) {
    label = account.isDeleted ? t("account.deleted", { email: account.email }) : account.email;
  }

  return <span title={accountId}>{label}</span>;
}
