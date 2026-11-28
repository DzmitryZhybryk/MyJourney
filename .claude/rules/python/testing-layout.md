---
paths:
  - "backend/tests/**"
  - "backend/pyproject.toml"
  - "backend/Makefile"
---

# Backend tests: layout, markers, fixtures, run targets

Where things live. How a test is written — `testing.md`. Commands run from `backend/`.

## Pyramid

Two orthogonal axes: **level** (speed and dependencies) and **domain** (mirror of `app/`).

| Level | Touches I/O? | Covers |
|---|---|---|
| **unit** | no | domain entities and VOs, application services on fakes, pure helpers, crypto/jwt roundtrips, adapters of external clients with the transport stubbed (`AioStubber` for S3) |
| **integration** | real Postgres, S3 emulator (RustFS) | repositories, UoW, SQL, `FOR UPDATE` locks, unique constraints, migrations; what only a real store shows — signature enforcement, bucket policy, CORS |
| **api** | ASGI app | routes, wiring, `resolve_http_status`, cookies, error envelope |

Most of the value is in `unit/`; keep integration and api thin.

Argon2 is deliberately slow (~50 ms/hash): service tests use `FakeSaltedHasher`; the real
`Argon2SaltedHasher` is covered once in `unit/shared/infra/crypto/` (roundtrip + wrong secret fails).

## Layout

Top level by level, then mirror `app/<domain>/<layer>`: `tests/<level>/<domain>/<layer>/test_*.py`.
Shared pieces: `tests/conftest.py`, `tests/fakes/`, `tests/builders.py`. Read the tree for the
current domains instead of assuming.

## Markers

Applied **automatically from the path** by `pytest_collection_modifyitems` in `tests/conftest.py`;
never hand-tag. Level and domain compose: `-m unit`, `-m users`, `-m "unit and users"`. A new level
or domain must be registered in `pyproject.toml` `markers`, the conftest tuples (`--strict-markers`
rejects unregistered ones) and, for a domain, a `test-<domain>` target in `backend/Makefile` — `make`
fails on an unknown target, so a missing one shows up as an error, not a green run.

The same hook caps each test's time by level (`_LEVEL_TIMEOUTS`, pytest-timeout). The cap exists so
that it is never raised without thought: a test that hits it is analysed first. A cause in the test or
in the code under test is fixed there. An objective cause that only a workaround would remove (a test
that spawns a process, a dependency the code legitimately imports) raises the cap in a small step —
for that test alone with `@pytest.mark.timeout` when only it is slow, for the level when the level as a
whole has grown — with the cause stated next to the new value. `--durations=5` lists the slowest tests
in every run, CI logs included.

## Where a fixture lives

pytest resolves fixtures only from `conftest.py` files above the test, and imports the root
`conftest.py` first. Add to the existing conftests; do not invent new layers. Use the narrowest
one that reaches every consumer:

- `tests/conftest.py` — suite-wide setup (env bootstrap, the marker hook) and fixtures reused
  across **levels**. The env bootstrap runs before any `app` import, so child conftests may import
  `app` at top level; the root itself keeps its app imports after the bootstrap (`# noqa: E402`).
- `tests/unit/conftest.py` — cross-domain, **unit-only** fixtures: stateless infra built with an
  explicit test config that bypasses `settings` (`jwt_service` with a literal secret).
  api and integration cannot reuse these, since the app decodes with `settings`.
- `tests/unit/<domain>/conftest.py` — the domain's service-under-test wired on fakes.

A fixture needed from another domain is **promoted up** to the right shared level, never copied.
Fixtures always live in a `conftest.py`, never inline in a `test_*.py` — even one used by a single
file: put it in a `conftest.py` in that file's own directory.

## Coverage

Gate 90% (`make coverage`, run by the pre-commit hook). Rough targets: domain ~90%, application
~80%; do not chase 100% on infra and presentation at the unit level.

## Run targets

Beyond CLAUDE.md's commands: `make test-unit` / `test-api`, `make test-<domain>`, and an
intersection `uv run pytest -m "unit and users"`. Integration stays out of `make check` on purpose.
