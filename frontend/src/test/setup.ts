/**
 * Global Vitest setup (wired via `test.setupFiles` in `vite.config.ts`).
 *
 * Does four things (plus a shared Testing Library wait timeout, see below):
 *  1. i18n: synchronously loads the `en` bundles onto the same singleton instance the code uses
 *     (in the app locales load lazily via dynamic `import()`, so without this `i18n.t(...)` would
 *     return the key itself). So `messageForCode` and the UI resolve real English texts: the real
 *     mapping is tested, not mocks.
 *  2. jest-dom: registers matchers (`toBeInTheDocument` etc.) in `expect`.
 *  3. jsdom polyfills: `matchMedia`, `ResizeObserver` and `IntersectionObserver`, which jsdom lacks
 *     but Mantine (Menu/Modal), the `GlobeCanvas` container and the feed use.
 *  4. MSW: the network layer of component tests: listen/reset/close, plus clearing module state
 *     (`tokenStore`, `sessionStorage`) and mocks after every test. Unit tests install their own
 *     `fetch` mock and bypass MSW (see `handlers.ts`).
 */

import "@testing-library/jest-dom/vitest";

import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

import { clearAccessToken } from "../auth/tokenStore";
import enAuth from "../locales/en/auth.json";
import enCommon from "../locales/en/common.json";
import enErrors from "../locales/en/errors.json";
import enJourneys from "../locales/en/journeys.json";
import { i18n } from "../i18n";
import { server } from "./handlers";
import { IntersectionObserverStub } from "./intersection";

i18n.addResourceBundle("en", "common", enCommon, true, true);
i18n.addResourceBundle("en", "auth", enAuth, true, true);
i18n.addResourceBundle("en", "errors", enErrors, true, true);
i18n.addResourceBundle("en", "journeys", enJourneys, true, true);

void i18n.changeLanguage("en");

// findBy*/waitFor wait 1 s by default. The first city pick in a file (a cold form render, the 250 ms
// autocomplete debounce and the MSW response) takes up to ~0.8 s under coverage and full core
// load, and the default occasionally gave up. A satisfied wait returns at once, so the margin only
// slows a failing test.
configure({ asyncUtilTimeout: 3000 });

// matchMedia: Mantine (Menu/Modal/visual hooks) uses it and jsdom has none. Assigned directly (not
// via vi.stubGlobal) so `vi.unstubAllGlobals()` in afterEach does not remove it.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList,
});

// ResizeObserver: absent in jsdom; the GlobeCanvas container and part of Mantine instantiate it.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;

// IntersectionObserver: absent in jsdom; the journey feed loads pages with it. The stub is
// controllable: the test triggers intersection itself (`intersectAllObserved`).
globalThis.IntersectionObserver = IntersectionObserverStub as unknown as typeof IntersectionObserver;

// scrollIntoView: absent in jsdom; Mantine Combobox (selectFirstOption/arrow navigation) calls it
// on the active option.
Element.prototype.scrollIntoView = () => {};

// window.scrollTo: jsdom reports "Not implemented" on every call; leaving a journey card restores
// the page scroll with it on narrow screens (the default in tests).
window.scrollTo = () => {};

// setPointerCapture: absent in jsdom; card dragging and map gestures capture the pointer with it.
Element.prototype.setPointerCapture = () => {};

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));

afterEach(() => {
  // Unmount the tree first (effect unsubscriptions), then clear network and state.
  cleanup();
  server.resetHandlers();
  clearAccessToken();
  // Node >= 26 injects its own localStorage/sessionStorage globals (the experimental Web Storage
  // API), which shadow jsdom's storage and break this clear(). They are disabled by the
  // --no-experimental-webstorage flag in NODE_OPTIONS of the test scripts (package.json); a no-op on node 22.
  sessionStorage.clear();
  // Persisted state (legend flag, banner dismiss, i18next language) lives in localStorage; clear it
  // so it does not leak into neighbouring tests.
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

afterAll(() => server.close());
