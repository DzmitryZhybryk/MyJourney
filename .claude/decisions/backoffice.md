# Backoffice: the read side of operator screens

## Operator screens that join several domains read a projection in `backoffice`
- `backoffice` listens to domain events and keeps one projection per consumer screen
  (`backoffice.accounts`) in its own Postgres schema. It calls no domain and writes into none: a leaf
  of the dependency graph.
- Projection fields are nullable in the output; an incomplete row is shown, not a 500.
- Why: the admin filters by fields of `auth` and `users` at once; only a joined copy can do that
  without coupling the domains.
- Rejected: composing the list from each domain's responses — no filter across both.
- Rejected: one domain leading and asking the other — couples them and filters only by its own fields.
- Rejected: `InvariantViolationError` on an incomplete row — one broken row would fail the whole list.
- Source: PR #241, 2026-11-23
