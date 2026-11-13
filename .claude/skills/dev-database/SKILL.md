---
name: dev-database
description: Use when working with the MyJourney dev database - applying, creating or rolling back Alembic migrations, loading the gazetteer datasets, recreating the dev DB from scratch, inspecting schema or running EXPLAIN against it, or previewing migration SQL for locks.
---

# Dev database operations

Schema and query design (indexes, locking, safe migrations) is the global `postgres` skill. This
one covers only how to reach and manage **this project's dev database**. There is no production
database on this host.

## Access

`POSTGRES_HOST=myjourney_pg` resolves only inside the docker network; from the host the port is
published as `5439`.

```bash
docker exec -it myjourney_pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'   # inside the container, simplest
(set -a; . ./.env; set +a; psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5439/$POSTGRES_DB")   # from the host, repo root
```

Never print or paste credentials; read variable names from `.env` (see global CLAUDE.md).

## Migrations (from the repo root)

`make run` applies pending migrations itself: the one-shot `myjourney_migrate` runs before app and
worker start. The targets below run a throwaway container of the same service
(`compose run --rm`), so the stack need not be up — only Postgres, which compose starts.

```bash
make migrate-create msg="description"  # autogenerate
make migrate-upgrade                 # apply, then the procrastinate schema (see below)
make migrate-downgrade               # roll back one (rev=<revision> for a specific one)
make migrate-history
make migrate-current
(cd backend && uv run alembic upgrade <base>:<head> --sql)    # SQL only, without applying - to inspect locks
```

The init migration is edited in place while there is no production.

## Procrastinate schema

The `procrastinate_*` tables are not in alembic: `python -m app.shared.infra.procrastinate` applies
them, and the `myjourney_migrate` service runs it right after `alembic upgrade head` in every
stack. Autogenerate ignores these tables (`include_name` in
`migrations/env.py`), so a new revision never proposes dropping them.

The command only checks that `procrastinate_jobs` exists, not which version of the schema is
there. After bumping procrastinate, look in the installed package's `procrastinate/sql/migrations/`
for files newer than the previous version: apply them by hand, or recreate the dev DB.

## Gazetteer datasets

The one-shot `myjourney_geo_load` loads the datasets listed in `manifest.toml` into the dev DB on
every `make run`, after the migrations and before app starts, and skips what is already loaded.
`make geo-load` (repo root) runs it alone. The dataset file is taken from `backend/.geo-cache` when
already downloaded.

## Recreate the dev DB from scratch

From the repo root:

```bash
make stop && docker volume rm myjourney_pg_data && make run
```

`make run` migrates and loads the gazetteer before app starts; the first load downloads the
datasets unless `backend/.geo-cache` already holds them.
