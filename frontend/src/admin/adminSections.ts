/**
 * Admin sections in menu order; a new section is one entry here plus its route in `App.tsx`.
 * `isWide` gives the section the wide content column, for tables that do not fit the form width.
 */
export const ADMIN_SECTIONS = [
  { key: "mediaConfig", path: "media-config", isWide: false },
  { key: "accounts", path: "accounts", isWide: true },
] as const;
