---
paths:
  - "backend/tach.toml"
  - "backend/tests/unit/shared/test_tach_layers.py"
---
# Editing `tach.toml`

An edge in `tach.toml` is an architecture decision, not build plumbing. The allowed shapes of an edge
are the tables in `backend/tests/unit/shared/test_tach_layers.py` — layers point inward, and another
domain is reached only from `infra` (a client implementing our own port) or `presentation` (wiring the
other domain's service). That test is the only copy of the table; read it, do not restate it.

- **Add an edge only when code being written needs it, and only in a shape the table already allows.**
  Copy an existing edge of the same kind (`journeys.infra → geo.application`), never invent a new one.
- **A forbidden edge means the code is in the wrong place**, not that the table is wrong: move the code,
  add a port in `application/ports/`, or call the other domain through a client in `infra`. If none fits,
  stop and ask the owner.
- **Never widen the tables in the test to make an edge pass.** Changing them is an owner decision.
- **Remove an edge tach reports as unused** in the same change.
- **Name every added or removed edge in the reply**, one line each — the owner does not read this file
  in diffs.

| The thought | The answer |
|---|---|
| "tach fails, adding the edge is the quickest fix" | The failure is the signal. Fix the import, not the declaration |
| "It's just one import from the other domain's `infra`/`domain`" | That import is the coupling that blocks extracting the domain |
| "`tach sync` will generate it" | `sync` copies whatever the code imports, violations included |
