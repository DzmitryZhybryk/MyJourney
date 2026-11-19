---
name: style-audit
description: Audit MyJourney frontend files (.tsx, .css, index.html) against the project's design-token policy and report (or fix) deviations. Use when the user asks to check style consistency, audit colors/fonts/sizes, verify design-token compliance, or align stray literal values to tokens.
---

# Style audit

Checks the visual files of `frontend/` against the token policy. Produces a report; edits only on
explicit request.

> **The skill does NOT list values** — a list kept by hand falls behind the code. The source of
> truth is `frontend/src/index.css` (`:root`) and `frontend/src/theme.ts`; the skill checks the
> **form** ("the value comes from a token"), not specific numbers.

## Scope

Audited:

- `frontend/src/**/*.tsx`
- `frontend/src/**/*.css`
- `frontend/index.html`

Out of scope:

- `frontend/node_modules/**`, `frontend/dist/**`, `frontend/coverage/**`
- Mantine internal classes (`.m_*`, hashed)
- comments, alt texts, console messages
- `src/assets/textures/**` (binary globe textures)

## Token layers

`index.css` holds **two layers**, and the split is not cosmetic:

1. **Palette** — named for WHAT it is: `--ink`, `--ink-2`, `--ink-deep`, `--ink-on-dark`,
   `--sun`, `--sun-deep`, `--glow`, `--on-sun`, `--sky`, `--sky-bright`, `--muted-on-dark`.
   Plus channel variants `--<name>-rgb` for translucent derivatives.
2. **Semantic** — named for WHY: `--surface`, `--surface-2`, `--surface-card`,
   `--text`, `--text-muted`, `--text-stamp`, `--text-error`, `--hairline`, `--accent`,
   `--accent-deep`, `--on-accent`.

**UI uses the semantic layer only.** Referencing the palette directly from a component
(`color: var(--ink-on-dark)` instead of `var(--text)`) is a violation: a name by color does not say
where it belongs, and `--ink` easily ends up in `color` where it is actually a background.

Exception: `index.css` itself, where the semantic layer is defined.

## What counts as a violation

### Color

- A raw `#hex` or `rgb()/rgba()` in `src/**` outside `index.css` → violation.
  Correct: `var(--<semantic token>)`, and for translucent values `rgb(var(--x-rgb) / α)`.
- Referencing the palette layer from a component instead of the semantic one → violation (above).
- Mantine props `c="slate.N"`, `c="dimmed"`, `c="red"` → violation: a second, independent color
  scale that knows nothing about the product surface. Correct: `c="var(--text-muted)"`,
  `c="var(--text-error)"` and so on.
- Allowed exceptions (check the context, do not flag blindly): pure `#fff`/`#000` and
  `rgba(255,255,255,·)`/`rgba(0,0,0,·)` in outlines and shadows of labels over the globe texture
  (`globe-label.css`, `globe-route.css`) — they need absolute contrast against an arbitrary
  background.

### Typography

- A literal `font-family` → violation. Only `var(--font-display)` (Lora, headings),
  `var(--font-body)` (system sans), `var(--font-mono)` (utility "stamps").
- A numeric `font-size` → violation. Only the scale steps `var(--fs-N)` from `index.css` — check
  the file for the current steps. Exception: `clamp(...)` on the landing's fluid headings.
- An error's font size matches body text: emphasis comes from weight and color, not size (see
  `rules/typescript/error-display.md`).

### Other axes

- A `transition` with a numeric micro-animation duration → `var(--dur-fast)`.
  Long transitions (camera flight, screen crossfade) have their own role; leave them.
- `backdrop-filter: blur(Npx)` for glass "chrome" → `var(--blur-glass)`.
- `border-radius` on action buttons → `var(--radius-action)`. `999px` pills are fine on navigation
  and badges (a different role), `50%` on circles.
- Breakpoints: there is no fixed set — desktop is the priority and a narrow screen only has to not
  break (`rules/web/performance.md` → UI quality). Do not flag `@media` thresholds.

### Component conventions

- `autoContrast: true` in `theme.ts` picks the label color on a filled button by itself.
  A manual `color=` / `!important` on a button label → violation: that button drops out of the
  common look of the others.
- Form errors: only `var(--text-error)`, weight 500, body size.
- Text on an accent fill: `var(--on-accent)`.

## Procedure

1. **Collect** across in-scope files:
   - `#[0-9a-fA-F]{3,8}\b`, `rgb(`/`rgba(`
   - `font-family`, the `font:` shorthand
   - `font-size`, JSX `fz=`
   - Mantine `c=` / `color=` with a string literal
   - `border-radius`, JSX `radius=`
   - `transition` with durations, `backdrop-filter: blur(`

2. **Check against the actual `:root`**, not memory:

   ```bash
   rg -n '^\s*--' frontend/src/index.css
   ```

   A token that is not there is not a token.

3. **Classify**: ✅ token · ⚠ literal, but the token is obvious · ❌ literal with no token
   (needs a decision: add a token or move to an existing one).

4. **Report by file**, with the proposed token:

   ```
   components/foo.css
     L42  color: #e8935c            → var(--accent)
     L58  font-size: 13px           → var(--fs-13)
   pages/Bar.tsx
     L17  c="dimmed"                → c="var(--text-muted)"
   ```

5. **Edits** only on explicit request. Afterwards re-check the touched files and run
   `npm run build` from `frontend/`.

## Notes for the auditor

- **Do not widen the scope into restructuring CSS** — token compliance only.
- **Check bulk regex replacements for self-references.** Replacing "value → `var(--x)`" easily hits
  the token's own definition and yields `--x: var(--x)`; such a property breaks silently while the
  build and tests stay green:

  ```bash
  rg --pcre2 -e '--([a-z0-9-]+):\s*var\(--\1\)' frontend/src --glob '*.css'
  ```

- **Replace font sizes only in `font-size:` and in the size slot of the `font:` shorthand** — the
  same numbers appear in `padding`, `width`, `gap`.
- A value that occurs ONCE with no token for it is not always a violation. Offer the choice: add a
  token, or keep it with a comment saying why the value is a one-off.
- `--lp-*` in `landing.css` are **not** duplicates but a deliberate layer of local aliases over the
  semantic layer (see the comment at the top of that file). Do not flag them as duplication.
- Compute contrast, do not eyeball it. AA thresholds: 4.5:1 for normal text, 3:1 for large text.
  Product surfaces: `--surface`, `--surface-card` (glass over it) — read their values from
  `index.css`.
