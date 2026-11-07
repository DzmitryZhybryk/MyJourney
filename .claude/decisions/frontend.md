# Frontend

## No icon library: icons are self-hosted Noto Emoji SVGs
- The SVGs live in `frontend/src/assets/emoji/` and render as `<img>`.
- Why: they look the same in every browser and OS, without a library for a handful of icons.
- Rejected: Tabler — ~5,900 icons for the 3–4 used, and its thin line icons looked flat.
- Rejected: Lucide, Phosphor, Solar — why not recorded.
- Rejected: raw Unicode emoji — each OS draws them its own way.
- Source: 2026-06-17

## A value edited in place is marked by a dashed underline at rest, through `EditableValue`
- Every screen marks its in-place editable values with `components/EditableValue.tsx`; read-only
  values next to them carry no underline. Actions (buttons) and settings (switches) keep their own form.
- Why: the user must see what can be changed without hovering, on touch screens too, and one
  screen must not invent its own sign.
- Rejected: a soft backing on hover only (until 2026-11-07) — invisible at rest and on touch; an
  editable year looked the same as the read-only distance.
- Rejected: an "Edit" link per field — noisy once a card has several editable fields.
- Rejected: accent colour on editable values — the accent means a primary action, and colour alone
  fails accessibility.
- Rejected: a pencil icon per field — icons are Noto Emoji only (entry above); a coloured pencil at
  every field looks toy-like.
- Rejected: an "Edit" mode for the whole card — breaks instant save with undo on the journey card.
- Source: PR #200, 2026-11-07
