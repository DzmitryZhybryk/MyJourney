// Playwright fixtures use the `use(...)` callback: it is the runner's API, NOT a React hook, but
// oxlint matches the name `use` against rules-of-hooks. The rule is silenced for the whole file.
/* eslint-disable react-hooks/rules-of-hooks */
import { test as base, type Page } from "@playwright/test";

import { loginViaUi, registerUser, type RegisteredUser } from "./helpers/users";

interface Fixtures {
  /** A freshly registered (via API) user; NOT yet logged in through the UI. */
  freshUser: RegisteredUser;
  /** A page that has already gone through a UI login as `freshUser`. */
  authedPage: Page;
}

/**
 * The base `test` with the project fixtures.
 *
 * Specs import `test`/`expect` from here, not from `@playwright/test`, to get `freshUser` (API
 * seed) and `authedPage` (an already logged-in page) without duplicating preconditions in every file.
 */
export const test = base.extend<Fixtures>({
  freshUser: async ({ request }, use) => {
    await use(await registerUser(request));
  },
  authedPage: async ({ page, freshUser }, use) => {
    await loginViaUi(page, { login: freshUser.username, password: freshUser.password });
    await use(page);
  },
});

export { expect } from "@playwright/test";
