/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://app:8000";

/**
 * Vitest test scope by extension: unit (`*.test.ts`, pure logic) vs component (`*.test.tsx`,
 * React render; JSX requires `.tsx`). Controlled by `VITEST_SCOPE` from the Makefile
 * (`make test-unit` / `make test-component`); both by default. e2e (`*.spec.ts`) is Playwright and
 * is not included here. The glob `*.test.ts` does not match `.test.tsx` (the extra `x`), so the split is clean.
 */
function resolveVitestInclude(): string[] {
  const scope = process.env.VITEST_SCOPE;
  if (scope === "unit") {
    return ["src/**/*.test.ts"];
  }

  if (scope === "component") {
    return ["src/**/*.test.tsx"];
  }

  return ["src/**/*.test.{ts,tsx}"];
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // In Docker on macOS bind-mount file events do not always reach the container and Vite serves a
    // stale module. Polling is enabled by the same flag set in ops/docker-compose.yaml; it is set
    // explicitly here rather than via chokidar's own environment variable.
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === "true" },
    proxy: {
      "/v1": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Per-test cap: a test near it is a defect to speed up, not a reason to raise the cap.
    testTimeout: 5000,
    // Only co-located unit/component tests from src (never `e2e/**/*.spec.ts`, those are Playwright).
    // The exact set depends on VITEST_SCOPE (see resolveVitestInclude).
    include: resolveVitestInclude(),
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/main.tsx",
        "src/**/*.d.ts",
        // SDK generated from OpenAPI: no hand-written code there, nothing to cover.
        "src/api/generated/**",
        // Declarative composition without logic: the route table and layout shells with <Outlet/>.
        // No branching; covered by e2e navigation, not unit/component. PublicLayout is trivial since
        // the globe moved to the root (header + <Outlet/> through a cross-fade).
        "src/App.tsx",
        "src/pages/journeys/JourneysLayout.tsx",
        "src/pages/PublicLayout.tsx",
      ],
      // Merge gate: coverage >= 90% (enforced by the pre-commit hook, not CI; see CLAUDE.md).
      thresholds: {
        statements: 90,
        branches: 90,
        functions: 90,
        lines: 90,
      },
    },
  },
});
