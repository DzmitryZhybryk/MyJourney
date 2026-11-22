# Permissions: what a token grants and how a route checks it

## Role, plan and expanded permissions travel in the access token; routes check permissions only
- `auth` expands role ∪ plan into a `permissions` list (`auth/domain/permissions.py`, the only copy of
  the map) and signs it into the token. A route declares `PermissionChecker(PermissionEnum.<…>)`; it never
  reads role or plan. Permission names are the token's contract, so they live in `shared/infra/jwt`
  (`PermissionEnum`), not in `auth.domain`, which other domains may not import. `plan` stays a claim
  only for future numeric limits a permission cannot express.
- Access TTL is 15 minutes: a demotion or an expired plan lives until the token expires.
- Why: no DB and no network on a guarded route — after the split every such check would otherwise be a
  call to `auth`. New roles, plan rights or per-user grants change only `auth`.
- Rejected: a DB lookup on guarded routes — a network call to `auth` per route after the split.
- Rejected: loading the user on every request with a `token_version` check (ai-recap) — a query on every
  click; the owner does not want it.
- Rejected: storing access tokens to revoke them — revocation needs a lookup per request, the same cost.
- Rejected: role in the token plus the map copied into `shared` — every service carries a copy, any role
  change redeploys all.
- Rejected: a separate `require_plan` guard — plan rights expand into permissions, one mechanism.
- Rejected: a permission name as a string literal in each route (until 2026-11-21) — a copy per route, a
  typo caught only by an api test; `PermissionEnum` makes it a type error.
- Revisit when: the permission list reaches hundreds (header size) — then the token carries role + plan
  and services cache the map from `auth`; routes do not change.
- Source: role model (#52), 2026-11-12

## A permission is named `<domain>.<resource>.<action>`; the member name is the value upper-cased
- `media.config.edit` → `MEDIA_CONFIG_EDIT`, `auth.accounts.read` → `AUTH_ACCOUNTS_READ`. The domain is
  the one that owns the data the route serves.
- Why: the owning domain is visible both in code and in the token; one form for every permission.
- Rejected: `auth.account_read` — a second spelling (underscore) beside the dotted form.
- Rejected: a name without the domain (`accounts.read`) — the owner of the permission is not visible.
- Source: admin account emails (#55), 2026-11-22

## The `user` role has an empty permission set
- Login grants the base access (ownership checks cut off other people's rows); the maps list only what
  is granted on top.
- Why: a permission everyone holds checks nothing.
- Rejected: base permissions on `user` for ordinary actions — every route would check a right nobody lacks.
- Revisit when: a role below the base level appears (read-only, banned, guest) — then base actions get
  permissions.
- Source: role model (#52), 2026-11-12

## A missing permission is 403 `permission_required`; a malformed permissions claim is 401
- Every claim is required: an absent `permissions` claim, or one that is not a list of strings, is
  `invalid_access_token` 401 like any other broken claim; the frontend refreshes and gets a full token.
- Why: the route is public in openapi, and the frontend must tell "no right" from "no session" to
  refresh once and retry. A broken claim must be loud, not a quiet 403.
- Rejected: 404 like someone else's row — that rule hides a row's existence, a route is not secret.
- Rejected: an `auth.` prefix on the code — the prefix on `invalid_access_token` is a documented
  leftover; shared codes carry none.
- Source: role model (#52), 2026-11-12
