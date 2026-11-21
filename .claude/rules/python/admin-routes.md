---
paths:
  - "backend/app/*/presentation/admin/**"
---
# Admin routes

The settled shape is `.claude/decisions/admin.md`; read it before adding or moving an admin route.

- An admin route lives in its domain's `presentation/admin/` and is mounted at `/v1/admin/{domain}`.
- It never imports a schema from the public `presentation/schemas.py`, and a public route never imports
  one from `presentation/admin/`; the same goes for the use case `*Result`. Overlapping fields today are
  not a reason to share: the next admin-only field would leak to anonymous clients.
- Every admin route depends on `PermissionChecker(PermissionEnum.<…>)` — the UI hiding the entry is not
  a check.
