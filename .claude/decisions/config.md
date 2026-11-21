# Domain config: values an operator changes without a redeploy

The reference implementation is media (`MediaConfigService`, table `media_config`, `shared/versioned_config/`);
a new `<domain>_config` repeats it.

## A domain's config is one versioned snapshot: insert-only rows, the latest version wins
- One table per domain (`VersionedConfigModel`): `version` PK, `created_at`, `created_by` (NULL = written by
  a deploy), the whole config as one JSONB snapshot (`PydanticJSONB`). Public read at
  `GET /v1/{domain}/config/`, admin read and edit under `/v1/admin/{domain}/config/`.
- The rows are the audit trail: no edit log. No per-domain cache: every use reads the latest row.
- A change of the snapshot's shape ships as a data migration that inserts a new version. Alembic
  autogenerate does not see it (the column stays `jsonb`), so it is written by hand. A forgotten one stops
  the deploy: the seed command reads the latest row with the new type and fails, so `app` never starts.
- Why: one shape for every domain; whole-config edits by one or two admins; old versions stay for audit.
- Rejected: a seed that tolerates an unreadable latest row and writes the defaults over it — silently
  reverts what an admin saved.
- Rejected: typed rows per kind with per-kind versions — a different table shape per domain.
- Rejected: a history list on the admin screen — old snapshots may not fit the current schema.
- Rejected: an in-process cache — caching is one shared mechanism, not per domain.
- Rejected: logging edited values (a secret could land in config) or edited field names (repeats the rows).
- Revisit when: the shared cache (`.plan/ideas/backend-cache.md`) exists.
- Source: #51, 2026-11-15..21

## The initial config is written by the migrate one-shot, only into an empty table
- The seed command runs after `alembic upgrade head` and checks for a row by reading before it inserts;
  a PK conflict from a parallel run is not an error.
- Why: a redeploy must never overwrite what an admin saved.
- Rejected: `ON CONFLICT DO UPDATE` — overwrites admin edits on every deploy.
- Rejected: `ON CONFLICT DO NOTHING` — Postgres logs the conflict as ERROR on every deploy.
- Source: #51, 2026-11-19

## An edit names the version it edited; any other version is 409
- The request carries `editedVersion`; a stale or a future one is `config_version_conflict`
  (`next_config_version`), and so is a PK conflict from a parallel save.
- Why: without it a second admin silently overwrites the first one's save.
- Rejected: last write wins — loses an edit without anyone noticing.
- Source: #51, 2026-11-21
