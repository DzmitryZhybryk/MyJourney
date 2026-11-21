import type { Credentials } from "./users";

/**
 * The admin of the throwaway e2e stack: registered and promoted by the `myjourney_e2e_admin` one-shot in
 * `ops/docker-compose.e2e.yaml`, which repeats these values. Only `make test-e2e` sets `E2E_HAS_ADMIN`:
 * the dev stack has its own admin, and the promote script refuses a second one.
 */
export const E2E_ADMIN: Credentials = { login: "e2e_admin", password: "e2e-Admin-Password-1" };

export const HAS_E2E_ADMIN = process.env.E2E_HAS_ADMIN === "1";
