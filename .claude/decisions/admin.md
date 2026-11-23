# Admin: the operator's surface of every domain

## Admin routes live under `/v1/admin/{domain}/`, inside the domain that owns the data
- Each domain keeps its admin routes in its own `presentation/admin/` package (`routes.py`, `schemas.py`,
  `responses.py`); `main.py` mounts the router at `/v1/admin/{domain}` with the tag `admin: {domain}`.
  The public routes stay at `/v1/{domain}/`.
- Why: one prefix gives the edge one place to restrict, rate-limit or move the admin to its own host, and
  Swagger groups the admin surface apart. Keeping the routes in the domain keeps it extractable: the
  domain owns both its public and its admin surface.
- Rejected: `/v1/{domain}/.../admin/` (a per-domain suffix the edge cannot match once); a separate
  `admin` domain calling every other domain (it would couple all domains through itself).
- Source: #51 (media config admin), 2026-11-21

## Admin and public routes never share a schema
- An admin route has its own `*Request`/`*Response` and its own use case `*Result`, even when today's
  fields overlap with a public one (`MediaConfigResponse` vs `UploadRulesResponse`).
- Why: an admin response carries what the operator needs (version, author, timestamps, raw values); a
  shared schema leaks that to anonymous clients the day a field is added for the admin.
- Source: #51, 2026-11-21

## Admin routes behind `PermissionChecker` may read other users' rows
- The owner-scoping invariants of `rules/python/authorization.md` bind user-facing routes; an admin
  route's guard is its permission (`find_user_credentials_by_user_ids` behind `auth.accounts.read`).
- Why: owner-scoping protects a user from other users, and the operator's job is exactly other users'
  data (account emails in "Кем").
- Rejected: owner-scoping admin reads too — an admin screen could show nothing but the admin's own rows.
- Rejected: routing such reads through a separate service — another boundary with the same guard; why
  not recorded.
- Source: #64 / PR #239, 2026-11-23

## The SPA admin is one section with its own menu; the UI checks the role
- The avatar menu has one "Admin" entry; `/admin` is a layout with a section menu on the left
  (`frontend/src/admin/adminSections.ts`), a new screen is one entry there plus a route.
- The entry and the `/admin` guard check `role === "admin"` from the access token, not permissions: all
  admins have the same rights. The backend still checks a permission on every admin request
  (`PermissionChecker`), so the UI check is visibility only.
- Rejected: one avatar-menu item per admin screen (does not scale past a few); per-permission
  visibility of the entry and sections (no admin with partial rights is planned).
- Revisit when: admins with different rights appear.
- Source: #51 Phase 3, owner, 2026-11-21
