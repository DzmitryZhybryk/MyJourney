# Frontend

## No icon library: icons are self-hosted Noto Emoji SVGs
- The SVGs live in `frontend/src/assets/emoji/` and render as `<img>`.
- Why: they look the same in every browser and OS, without a library for a handful of icons.
- Rejected: Tabler — ~5,900 icons for the 3–4 used, and its thin line icons looked flat.
- Rejected: Lucide, Phosphor, Solar — why not recorded.
- Rejected: raw Unicode emoji — each OS draws them its own way.
- Source: 2026-06-17
