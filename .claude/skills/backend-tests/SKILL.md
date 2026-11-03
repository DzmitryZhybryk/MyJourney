---
name: backend-tests
description: Write or extend backend unit tests for the MyJourney FastAPI service (DDD, pytest, async). Use when the user asks to write/add/cover backend tests, test a domain/service/entity, or scaffold the test suite. Conventions are in .claude/rules/python/testing.md and testing-layout.md. Unit tests by default; integration and api only on explicit request.
---

# Backend tests

Write backend tests for `backend/` following the project's testing constitution. All commands run
from `backend/` (self-contained uv project).

## Source of truth

Conventions live in `.claude/rules/python/testing.md` (style, fakes, determinism) and
`.claude/rules/python/testing-layout.md` (levels, layout, markers, fixture placement, targets).
They load when Claude reads anything under `backend/tests/`; read both explicitly before the first
test of a session. Do **not** restate or fork them here — this skill is only the *procedure*.

## Scope

- **Default focus: `unit/`** (domain entities/VO, application services with fakes, pure helpers,
  crypto/jwt roundtrips). This is where the value is.
- `integration/` (real Postgres) and `api/` (ASGI app) are **separate phases** — only touch them
  when the user explicitly asks.

## Procedure

1. **Locate the target.** Read the code under test in `backend/app/<domain>/<layer>/`. Identify
   branches/invariants worth covering (e.g. `AuthService.refresh` reuse-detection, timing
   mitigation in `login`, idempotent `revoke()`).
2. **Mirror the layout.** Place the test at the path the existing suite dictates — read
   `backend/tests/` rather than assuming. **Never hand-tag markers:** the
   `pytest_collection_modifyitems` hook in `tests/conftest.py` applies level and domain markers
   from the file path.
3. **Prepare fakes (boundary only).** Reuse or add an in-memory fake in `backend/tests/fakes/`,
   shaped per `testing.md` → "Fakes over mocks". When writing the **first** fake for a
   repository, add its port (a thin `Protocol`, only the methods used) and type both the real
   repo and the fake with it — placement and imports per `layers.md` → "Outbound ports", the
   name per `naming.md`.
4. **Add builders** in `backend/tests/builders.py` only when the same construction repeats across
   files (`testing.md` → "Test data builders", "Reuse before create").
5. **Write the test** to the conventions of `testing.md`: naming, state-based assertions,
   parametrized variants, determinism.
6. **Verify green:**
   ```bash
   cd backend
   uv run pytest -m unit            # or the specific test file
   make lint                        # ruff (PT rules included)
   make typecheck                   # ty — catches fake/Protocol drift
   ```
7. **Coverage.** `make coverage`. The 90% threshold is already enforced (`--cov-fail-under=90`
   in the Makefile, forced by the pre-commit hook) — below it the code does not merge, so check
   before committing rather than after.
8. **Review (optional).** For non-trivial additions, offer to run `/code-review` on the diff.

## Notes

- Repositories are not unit-tested — that's the integration phase.
- Don't assert private internals (`service._uow`) — ruff `SLF001` will flag it.
