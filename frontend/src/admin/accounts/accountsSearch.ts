import type { ListAccountsData, SortDirectionEnum } from "../../api/sdk";

/** Rows per page; sent explicitly, so the counter never depends on the backend default. */
export const PAGE_SIZE = 20;

// Upper bounds of the backend query params: a hand-edited URL beyond them would answer 422.
const MAX_PAGE = 10_000;
export const EMAIL_MAX_LENGTH = 254;
export const DISPLAY_NAME_MAX_LENGTH = 50;
const ROLE_MAX_LENGTH = 50;

export type ConsentFilter = "any" | "yes" | "no";

/** The list state kept in the URL; an empty string is "no filter". */
export interface AccountsSearch {
  page: number;
  email: string;
  displayName: string;
  role: string;
  consent: ConsentFilter;
  includeDeleted: boolean;
  sortDirection: SortDirectionEnum;
}

export type AccountsFilters = Omit<AccountsSearch, "page" | "sortDirection">;

export const NO_FILTERS: AccountsFilters = {
  email: "",
  displayName: "",
  role: "",
  consent: "any",
  includeDeleted: false,
};

const PARAMS = {
  page: "page",
  email: "email",
  displayName: "name",
  role: "role",
  consent: "consent",
  includeDeleted: "deleted",
  sortDirection: "sort",
} as const;

function readText(params: URLSearchParams, name: string, maxLength: number): string {
  return (params.get(name) ?? "").trim().slice(0, maxLength);
}

function readPage(params: URLSearchParams): number {
  const page = Number(params.get(PARAMS.page));
  return Number.isInteger(page) && page >= 1 ? Math.min(page, MAX_PAGE) : 1;
}

function readConsent(params: URLSearchParams): ConsentFilter {
  const consent = params.get(PARAMS.consent);
  return consent === "yes" || consent === "no" ? consent : "any";
}

/** The list state from the URL; anything missing or malformed falls back to the unfiltered first page. */
export function readAccountsSearch(params: URLSearchParams): AccountsSearch {
  return {
    page: readPage(params),
    email: readText(params, PARAMS.email, EMAIL_MAX_LENGTH),
    displayName: readText(params, PARAMS.displayName, DISPLAY_NAME_MAX_LENGTH),
    role: readText(params, PARAMS.role, ROLE_MAX_LENGTH),
    consent: readConsent(params),
    includeDeleted: params.get(PARAMS.includeDeleted) === "1",
    sortDirection: params.get(PARAMS.sortDirection) === "asc" ? "asc" : "desc",
  };
}

/** The URL params of the list state, without the values that match the unfiltered first page. */
export function writeAccountsSearch(search: AccountsSearch): URLSearchParams {
  const params = new URLSearchParams();
  if (search.page > 1) params.set(PARAMS.page, String(search.page));
  if (search.email) params.set(PARAMS.email, search.email);
  if (search.displayName) params.set(PARAMS.displayName, search.displayName);
  if (search.role) params.set(PARAMS.role, search.role);
  if (search.consent !== "any") params.set(PARAMS.consent, search.consent);
  if (search.includeDeleted) params.set(PARAMS.includeDeleted, "1");
  if (search.sortDirection === "asc") params.set(PARAMS.sortDirection, "asc");
  return params;
}

export function hasFilters(search: AccountsSearch): boolean {
  return (
    search.email !== NO_FILTERS.email ||
    search.displayName !== NO_FILTERS.displayName ||
    search.role !== NO_FILTERS.role ||
    search.consent !== NO_FILTERS.consent ||
    search.includeDeleted !== NO_FILTERS.includeDeleted
  );
}

export function toListAccountsQuery(search: AccountsSearch): NonNullable<ListAccountsData["query"]> {
  return {
    page: search.page,
    limit: PAGE_SIZE,
    email: search.email || undefined,
    displayName: search.displayName || undefined,
    role: search.role || undefined,
    marketingEmailsConsent: search.consent === "any" ? undefined : search.consent === "yes",
    includeDeleted: search.includeDeleted,
    sortDirection: search.sortDirection,
  };
}
