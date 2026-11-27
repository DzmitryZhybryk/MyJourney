import type { UserPlanEnum, UserRoleEnum } from "../../api/sdk";

// Keyed by the generated unions: a role or plan added on the backend fails typecheck until it has a label.
export const ROLE_LABEL_KEYS = {
  user: "accounts.roles.user",
  admin: "accounts.roles.admin",
} as const satisfies Record<UserRoleEnum, string>;

export const PLAN_LABEL_KEYS = {
  free: "accounts.plans.free",
  premium: "accounts.plans.premium",
} as const satisfies Record<UserPlanEnum, string>;

/** The i18n key of a value from the list, or `null` for a value this build does not know yet. */
export function labelKeyOf<K extends string>(labelKeys: Readonly<Record<K, string>>, value: string): string | null {
  return Object.hasOwn(labelKeys, value) ? labelKeys[value as K] : null;
}
