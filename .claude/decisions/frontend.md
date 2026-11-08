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

## The dev Vite server runs on the host, not in Docker
- `make run` starts the backend and infrastructure; `make fe-dev` starts Vite on the host, proxying
  `/v1` to the published `app` port. The e2e stack still runs Vite in a container (a fresh stack
  creates no files mid-run).
- Why: Docker Desktop's VirtioFS on macOS does not deliver file creation from the host to the
  container (directory mtime stays cached, no inotify create event), so Vite served a new file's
  first version until restart. Edits to existing files did arrive.
- Rejected: polling (`usePolling`, `CHOKIDAR_USEPOLLING`) — reads the same cached attributes; tried and failed.
- Rejected: `docker compose watch` sync — without a running watch the whole frontend freezes silently.
- Rejected: gRPC FUSE or OrbStack — each has its own host-to-container sync bugs.
- Rejected: atomic writes (temp + rename) — editors, git and Claude all write in place.
- Rejected: dev served like prod (`vite build --watch` + nginx) — loses HMR; prod parity is `make test-e2e`.
- Rejected: Podman — `podman machine` has the same Mac-to-VM VirtioFS boundary.
- Revisit when: a container on Docker Desktop sees a host-created file through inotify or polling
  (probe described in the Podman backlog task).
- Source: PR #205, 2026-11-08
