---
paths:
  - "frontend/src/**/*.test.ts"
  - "frontend/src/**/*.test.tsx"
  - "frontend/src/test/**"
  - "frontend/e2e/**"
  - "frontend/vite.config.ts"
  - "frontend/playwright.config.ts"
---

# Frontend tests: pyramid, tooling, environment, CI

How a test is written — `testing.md`. All commands run from `frontend/`.

## Pyramid

| Type | Environment | Covers |
|---|---|---|
| **unit** | none (pure logic) | `api/` helpers, `auth/` token / jwt / events logic, zod schemas, pure utils |
| **component** | jsdom | a React component: render → interact → assert what the user sees |
| **e2e** | real browser + stack | full flows in Chromium / Firefox / WebKit on a throwaway stack |

Most of the value is in unit tests of the `api` / `auth` modules. Keep component tests thin (forms,
dialogs, the banner) and e2e the thinnest — critical happy paths only. e2e flows are tagged with
codes (A/B/D/K/L…) in the docstrings of the specs; there is no separate plan file.

## Tooling

- **Vitest** reuses `vite.config.ts`; the `test` block sets `environment: "jsdom"`,
  `setupFiles: ["./src/test/setup.ts"]`, v8 coverage and `testTimeout` — the per-test cap. A test
  near the cap is analysed before anything changes: a cause in the test or the code is fixed there; an
  objective one that only a workaround would remove raises the cap in a small step, for that test alone
  when only it is slow, with the cause stated next to the new value.
- **Testing Library** (`react`, `user-event`, `jest-dom`) for components; **MSW** for the network in
  component tests; **Playwright** for e2e.
- Scripts: `npm run test` (watch), `test:run` (one-shot), `coverage`. The suite splits by
  `VITEST_SCOPE` (read in `vite.config.ts` → `resolveVitestInclude`): `test:unit` runs
  `src/**/*.test.ts`, `test:component` runs `src/**/*.test.tsx`; unset runs both. `make test`,
  `test-unit`, `test-component` mirror these. e2e (`*.spec.ts`) is Playwright and never matched here.

## jsdom quirks

- `sessionStorage`, `localStorage`, `atob`, `btoa` exist. `fetch` is stubbed per test
  (`vi.stubGlobal`). **`matchMedia` does not exist**; `src/test/setup.ts` already stubs some globals —
  read it before adding a stub. Its `IntersectionObserver` is controllable: the test triggers
  intersection itself (`intersectAllObserved` from `src/test/intersection.ts`).
- **No layout and no `AnimationEvent`.** Every rect is zero, so anything that measures (dnd-kit,
  FLIP) needs stubbed `getBoundingClientRect` / `offsetTop` (`src/test/layout.ts` or a per-test spy).
  Without `AnimationEvent`, React listens to `onAnimationEnd` on the prefixed `webkitAnimationEnd`
  and `fireEvent.animationEnd` drops `animationName`: dispatch
  `new Event("webkitAnimationEnd")` with `animationName` defined on it.

## Traps

- Run Vitest only through `npm run` / `make`. A direct `npx vitest` skips the scripts'
  `NODE_OPTIONS=--no-experimental-webstorage`, and on Node ≥ 26.5 every test then fails on an
  undefined `localStorage`.
- Mantine Combobox options stay hidden in jsdom (no computed position): find them with
  `findByRole("option", { name, hidden: true })`. With two fields offering the same option, scope
  the search to the field's own listbox — `within(document.getElementById(input.getAttribute("aria-controls")))`.
  Mantine `Select` puts its label on two inputs, so target the trigger by placeholder.
- e2e: WebKit drops `Secure` cookies over `http://localhost`, so the cookie flows are skipped on
  WebKit (`WEBKIT_SECURE_COOKIE_REASON`); lift the skip only with an https `E2E_BASE_URL`.
- e2e: argon2 hashing saturates the CPU under full parallelism — that is why `workers` is capped and
  `expect.timeout` is 15 s.
- e2e stack healthchecks hit `127.0.0.1`, never `localhost`: alpine resolves `localhost` to `::1`
  first, and the dev servers listen on IPv4 only.

## Layout

Test files are **co-located** with the module: `jwt.ts` → `jwt.test.ts` in the same folder. Shared
infrastructure is `src/test/` (not a mirror tree). e2e is `e2e/<domain>/<flow>.spec.ts` plus
`e2e/helpers/` and `e2e/fixtures.ts`.

## Coverage

`make coverage` (`@vitest/coverage-v8`) enforces a 90% threshold via `thresholds` in `vite.config.ts`;
the pre-commit hook runs it (see the `git-workflow` skill). The v8 **text** reporter silently hides
files already at 100%: for exact per-file numbers use `--coverage.reporter=json-summary` and read
`coverage/coverage-summary.json`. Do not chase 100% on components and pages.

## CI and e2e

- CI (`.github/workflows/ci.yml`) runs the **Frontend gate**: node → `npm ci` → `make check`
  (lint + typecheck + unit/component) on every PR. e2e runs only in `prod.yml`: on a PR into `main`
  and on a push to `main`.
- `make test-e2e` starts a throwaway stack (`ops/docker-compose.e2e.yaml`), runs Playwright and
  tears it down with `-v`. `make test-e2e-dev` runs against the already-running dev stack
  (`make run`): faster, but it **writes users into the dev database**. Narrow a run with
  `E2E_ARGS="--project=chromium"`.
- Playwright browsers live on the **host**, not in a container. After a package update run
  `npx playwright install`. A mismatch shows as "Executable doesn't exist at
  …/chromium_headless_shell-<N>" with N different from `~/Library/Caches/ms-playwright/`.
- Manual-only checks that no test sees (visuals, Lighthouse, cross-browser, responsive) —
  `web/performance.md` → "UI Quality".
