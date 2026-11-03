---
paths:
  - "frontend/src/**"
  - "frontend/index.html"
  - "frontend/vite.config.ts"
  - "frontend/scripts/check-bundle-budget.ts"
  - "frontend/scripts/check-mantine-styles.ts"
---

# Web performance (`frontend/`: React + Vite + Mantine)

## Core Web Vitals targets

| Metric | Target |
|---|---|
| LCP | < 2.5 s |
| INP | < 200 ms |
| CLS | < 0.1 |
| FCP | < 1.5 s |

## Bundle budget (gzipped)

| Page | JS | CSS |
|---|---|---|
| Landing | < 200 kb | < 25 kb |
| App page | < 300 kb | < 30 kb |

The numbers are a working agreement set by measurement, not a physical limit. Exceeding one is a
reason to look at what grew, not an alarm: if nothing removable is found, raise the limit **and
write down why the new number is reachable**. A budget that cannot be met teaches people to ignore
the table.

- **Check with `make fe-budget`, not by hand.** It builds with the Vite manifest, walks each route's
  **static import graph** (entry + lazy layout + page) and fails when a page exceeds its limit.
  Measure the graph of static imports, never the entry size: a dynamic `import()` lands in the
  preload manifest and is easily misread as a static dependency.
- The limits are duplicated in `frontend/scripts/check-bundle-budget.ts`; change both together. A new
  lazy route must be added to that script's page list or it goes unmeasured.
- Before optimizing, look for something on the critical path that the page never renders. That is
  what paid off so far: a dialog imported statically into the root provider (now `lazy`), and the
  generated SDK validators on classic zod (now `zod/mini`).
- Mantine is the one large block and removing it from the landing is not worth it: `MantineProvider`
  sits at the root and the public header's language switcher uses Mantine `Menu`; `/login` and
  `/signup`, the next step, load the same chunks anyway.
- Mantine CSS is loaded per component, never as the whole `@mantine/core/styles.css`:
  `frontend/src/mantineStyles.ts` imports only the stylesheets the used components need, in the order
  of `styles.css`. Importing a new Mantine component fails `make fe-mantine-styles` (part of `check`)
  until its stylesheets are added; the check prints the expected list. Never split these imports
  across pages: chunk load order is not cascade order.
- After a Mantine upgrade, look through the screens: a stylesheet moved or renamed upstream leaves a
  component unstyled with every check green.

## Loading

- Preload only the hero image and the primary font.
- Heavy libraries (`react-globe.gl`, `three.js`): dynamic `import()` only on the globe page.
- Defer non-critical CSS and JS.

## Images

- Always explicit `width` and `height`.
- Hero: `loading="eager"` + `fetchpriority="high"`; below the fold: `loading="lazy"`.
- AVIF/WebP with fallbacks; never serve an original larger than the rendered size.

## Fonts

At most 2 families, `font-display: swap`, preload only the critical weight.

## Animation

- Animate only compositor-friendly properties (`transform`, `opacity`).
- `will-change` sparingly, removed afterwards.
- JS animation through `requestAnimationFrame` or a library; no heavy scroll handlers (use `IntersectionObserver`).

## UI quality (manual checks)

Automated tests cannot see how it **looks**. Before merging a UI change:

- **A11y:** axe-core / Lighthouse a11y, keyboard navigation, `prefers-reduced-motion`, WCAG AA contrast (4.5:1 / 3:1).
- **Performance:** Lighthouse on key pages (login, signup, home, globe); INP during globe interaction.
- **Cross-browser:** Chrome / Firefox / Safari (desktop).
- **Responsive:** desktop is the priority; on narrow screens the layout only has to not break and
  decoration is hidden (mobile will be a separate Flutter app). Tap targets ≥ 44×44 px.
