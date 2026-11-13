---
paths:
  - "backend/app/**"
---
# Soft-delete: read policy

A repository over rows with a `deleted_at` column follows a two-tier convention:

- **Point lookups** (`find_<entity>_by_id`, …) carry **no** SQL predicate on `deleted_at`:
  the repository returns what the store holds, and interpreting deletion is domain work — an
  entity guard (`ensure_not_deleted()`) at the use-case call site, with a use-case-specific
  error (404 vs 410 vs "admin sees everything").
- **List queries** filter `deleted_at IS NULL` **in SQL by default** — fetching deleted rows
  only to drop them in Python is waste. State the filtering in the method's docstring.
- Extend for consumers of deleted rows **on demand, not up front**: a two-state kwarg
  `include_deleted: bool = False` on the method that needs it; "deleted only" — a separate
  method with a qualifier in its name. Never a tri-state `is_deleted: bool | None` — the
  `None` semantics cannot be read at the call site.
