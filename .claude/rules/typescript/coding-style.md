---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# TypeScript coding style (`frontend/`)

Extends `common/coding-style.md`. User-facing error display — `error-display.md`.

## Types

- Exported functions, component props and shared utils: explicit parameter and return types. Locals: let TS infer.
- `interface` for object shapes that may be extended or implemented; `type` for unions, intersections,
  tuples, mapped and utility types.
- String-literal unions over `enum`, unless interop demands one.
- Collections in signatures, props, fields and module constants are `readonly T[]` /
  `ReadonlySet<T>` / `ReadonlyMap<K, V>`. A mutable type is for a local accumulator, for state
  that really is mutated in place (a listener `Set`, a `useRef` map), and for values handed to a
  library typed as mutable (TanStack `InfiniteData.pages`; react-globe.gl data props get a cast).
- `any` is forbidden in application code. External or untrusted input is `unknown` plus safe
  narrowing; a dependence on the caller's type is a generic.

## React

- Props through a named `interface` or `type`; callback props typed explicitly.
- No `React.FC` without a specific reason.
- Immutable updates by spread (`{ ...user, name }`); never mutate props or state.

## Errors and validation

- `async/await` with `try/catch`; the caught value is `unknown`, narrowed with `instanceof Error`.
- Schema validation with **Zod** at boundaries (HTTP, forms); infer the type with `z.infer<typeof schema>`.
- Import it as `import * as z from "zod/mini"`, never from `"zod"`. The generated SDK validators are
  `zod/mini` too (`compatibilityVersion: "mini"` in `openapi-ts.config.ts`); one classic import puts
  full zod (~18 kb gz) back on every page.

## Naming

Variables and functions `camelCase`; types, interfaces, components `PascalCase`; constants
`UPPER_SNAKE_CASE`; hooks `useXxx`; booleans `is`/`has`/`should`/`can`.

## No `console.log` in production code

## Comments

The owner does not read frontend code, so a comment is written for the AI assistant that maintains
it, **only in English** (`.ts`, `.tsx`, `.css`, `index.html`, `nginx.conf`, `Dockerfile`, `Makefile`
under `frontend/`, tests included).

- Keep a comment only if it carries what the code does not show: a hidden constraint, a browser /
  jsdom / library quirk, why an obvious alternative is wrong, a contract with another file.
- No history ("used to be…"), metrics, or the fix that introduced the line; no restating the code.
- One or two lines. No `Args:` / `Returns:` blocks (that is the Python style).
- Strings are not comments: user-facing text stays in `src/locales`, and `it("...")` / `describe`
  titles stay Russian (see `testing.md`).
