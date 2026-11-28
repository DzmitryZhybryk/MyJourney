---
paths:
  - "frontend/src/**/*.test.ts"
  - "frontend/src/**/*.test.tsx"
  - "frontend/src/test/**"
  - "frontend/e2e/**"
---

# Frontend tests: philosophy and style

How a frontend test is written. Pyramid, tooling, jsdom quirks, layout, coverage, CI and e2e —
`testing-layout.md`. Mirrors the backend rule `python/testing.md`: unit-first, classicist,
mock only the I/O boundary. Commands run from `frontend/`.

## Classicist, mock only the network

- Assert what the user sees, the returned value, or the resulting state — never call order or
  component internals (props, hooks, state).
- The only mocked boundary is the network: `fetch` through `vi.stubGlobal` in unit tests, **MSW**
  in component tests. Never mock `appFetch` or other internal modules. Everything below the network
  (token store, jwt decode, error mapping, zod) runs real.
- Query like a user: `getByRole` / `getByLabelText` / `findByText`, not `data-testid` or CSS classes.
- `vi.fn()` spies only for side-effect collaborators whose *call* is the behaviour under test
  (`form.setFieldError`, an emitted event listener). Prefer observing resulting state.

## Determinism

- **Time:** build inputs with explicit values (a JWT `exp` baked into the test token). Use
  `vi.useFakeTimers()` only for code that reads "now" (cooldowns, debounce), locally, never globally.
- **Opaque values** (tokens, ids): assert the invariant (`Authorization` equals
  `Bearer ${theTokenWeStored}`), never a predicted value.
- **Module-level state is the main hazard.** `client.ts` (`pendingRefresh`), `tokenStore` and `events`
  hold state on the module. Reset in `beforeEach`: `clearAccessToken()`, `sessionStorage.clear()`,
  `vi.unstubAllGlobals()`, and `vi.resetModules()` when a fresh instance is needed. No test depends
  on another's leftovers.
- **Controlling async** (single-flight refresh): a deferred promise, a `fetch` stub resolved by hand,
  so two callers are provably in flight together; then assert `fetch` was called once.

## Reuse before create

Before adding a helper, fixture, MSW handler or render wrapper, scan what exists:

```bash
rg -n "export (function|const)" src/test
rg -n "vi\.stubGlobal|http\.(get|post)" src
```

- The shared seams are in `src/test/` (`render.tsx`, `handlers.ts`, `setup.ts`). Extend them; do not
  fork a near-duplicate beside one test.
- No file-local data helpers when a shared one fits. Build small inputs inline; promote to
  `src/test/` only when the same construction repeats across files.
- MSW handlers are the frontend's `tests/fakes/`: full reusable handlers in `src/test/handlers.ts`,
  overridden per test with `server.use(...)` for error cases.

## Conventions

- Import test APIs explicitly from `vitest`, only what the file uses. No `globals: true`.
- `describe` per unit or component, flat `it` inside; no deeper nesting. Subset with `-t`.
- `describe` / `it` titles are one-line **Russian**: `it("возвращает null для токена не из трёх частей", ...)`.
- `async/await`; `await expect(...).rejects.toThrow(...)` for throwing paths; `findBy*` over `getBy*`
  when the DOM updates after an await.
- Explicit options everywhere, including `getByRole("button", { name: "Sign in" })`.
- No `any` in tests; oxlint applies to test files like production code.
- Reset in `beforeEach`, clean up in `afterEach` (`vi.unstubAllGlobals()`, `vi.restoreAllMocks()`).
- A heavy component's tests split by scenario, `<Module>.<topic>.test.tsx`: Vitest runs files in
  parallel but tests inside one file in sequence, so one slow file sets the wall time. Shared helpers
  for such files live in `src/test/`.

## Anti-patterns

- Asserting on component internals or call order.
- Mocking internal modules instead of the network.
- Querying by `data-testid` or CSS class when a role, label or text query works.
- Leaking module state between tests.
- Faking timers or the clock globally.
- Recreating an existing render wrapper or handler.
