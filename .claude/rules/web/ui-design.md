---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.css"
  - "frontend/index.html"
---

# UI design work

Any task that designs a new screen or component, or reshapes the look of an existing one (layout,
palette, typography, spacing, motion, empty and loading states), starts by invoking the
`frontend-design:frontend-design` skill. Do it **before** proposing or writing the markup, and
without being asked: the owner designs the frontend continuously, and a design done without the
skill is a missed step.

- Not needed for a purely functional change that leaves the look alone (a bug fix, wiring, a type).
- Visible UX decisions (hiding content, changing behaviour) still need the owner's approval first.
- After the design lands, `style-audit` checks it against the design-token policy
  (`frontend/src/index.css` `:root`, `frontend/src/theme.ts`).
- Build the real page in the feature branch, not a prototype in `/sandbox`.
