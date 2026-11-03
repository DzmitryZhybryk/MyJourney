import { vi } from "vitest";

/**
 * Enables media queries whose text contains one of the fragments; the rest do not match, as in the
 * default stub in `setup.ts`. Undone by `vi.restoreAllMocks()`.
 */
export function matchMediaQueries(...fragments: string[]): void {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: fragments.some((fragment) => query.includes(fragment)),
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  );
}

/**
 * Enables `prefers-reduced-motion: reduce`: code that checks this setting replaces animations with
 * an instant change. Other media queries do not match. Undone by `vi.restoreAllMocks()`.
 */
export function preferReducedMotion(): void {
  matchMediaQueries("prefers-reduced-motion");
}
