import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { findAccountsByIdsOptions, type AccountItem } from "../api/sdk";

/**
 * An account as the admin sees it:
 * - `AccountItem`: auth knows the account (possibly marked deleted);
 * - `null`: auth answered without it, the account no longer exists;
 * - `undefined`: still loading or the request failed, show the raw id.
 */
export type AccountLookupResult = AccountItem | null | undefined;

export type AccountLookup = (accountId: string) => AccountLookupResult;

const NOTHING_LOADED: AccountLookup = () => undefined;

/**
 * Accounts by id for admin screens that store only an author id. Ids are normalized, so order and
 * duplicates do not change the request or the cache.
 *
 * Pass the ids of one screen page, never of a whole collection: the backend accepts at most 100,
 * and a list that can grow past that is paginated, so one page stays within the limit. More ids
 * fail without a request and the labels stay raw ids.
 */
export function useAccountsByIds(accountIds: Iterable<string>): AccountLookup {
  const idsKey = [...new Set(accountIds)].sort().join(",");
  const ids = useMemo(() => (idsKey ? idsKey.split(",") : []), [idsKey]);

  const { data } = useQuery({
    ...findAccountsByIdsOptions({ query: { ids } }),
    enabled: ids.length > 0,
    // Emails do not change while the screen is open; the default refetch on focus only repeats the request.
    staleTime: Infinity,
  });

  return useMemo<AccountLookup>(() => {
    if (!data) {
      return NOTHING_LOADED;
    }

    const accounts = new Map(data.accounts.map((account) => [account.id, account]));
    return (accountId) => accounts.get(accountId) ?? null;
  }, [data]);
}
