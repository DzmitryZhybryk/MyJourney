---
paths:
  - "backend/openapi.json"
  - "backend/tests/api/test_openapi_schema.py"
  - "frontend/src/api/generated/**"
  - "frontend/openapi-ts.config.ts"
  - "frontend/data/**"
  - "frontend/src/data/world-countries.topo.json"
  - ".github/workflows/**"
---

# Generated artifacts and drift gates

The frontend contract is generated from OpenAPI, so git holds two derived artifacts:
`backend/openapi.json` and `frontend/src/api/generated/`. Each can go stale independently and has
its own gate:

- **backend** — snapshot test `tests/api/test_openapi_schema.py`, part of `make check` / `check-ci`;
- **frontend** — a CI step: `make generate-api` + `git diff --exit-code`.

**A red gate is fixed by rebuilding, never by hand-editing the artifact:**
`make be-openapi-dump`, then `make fe-generate-api`, both results in the same commit.

## Dependabot cannot do this

A fastapi / pydantic bump changes how the schema renders; an `@hey-api/openapi-ts` bump changes
generator output. Either turns the gate red on the bot's branch, and a human pushes the rebuild
commit into it.

## The generator pin

`@hey-api/openapi-ts` is pinned to an **exact** version: it is pre-1.0 and minor releases change
output. The pin is on a prerelease line (`0.0.0-next-*`) out of necessity: the stable line crashes
on TypeScript 7 (`ts.SyntaxKind` is missing from the native compiler) while the prerelease does not
use the compiler API at all. Lift it when TS 7 ships in a stable generator release (last checked
2026-10-01: stable 0.99.0 still crashes).

Side effects of the pin:

- By semver `0.0.0-next-*` is below any stable version, so dependabot flags every advisory with a
  range "`< X.Y.Z`" even when the fix is already in the prerelease. **Verify against the code**: the
  vulnerable generator code is copied into `frontend/src/api/generated/`, look there. (GHSA-hhx9-57xq-r5rw
  is closed that way: the slots in `core/params.gen.ts` are already `Object.create(null)`.)
- The `overrides` entry for `js-yaml` in `frontend/package.json`: the prerelease's schema parser
  pulls a version from a vulnerable range and `make check` goes red on `npm audit`. The override
  raises only that transitive package and is dropped together with the pin.

## World-country borders (same pattern)

Source `frontend/data/world-countries.geo.json` (contract and provenance in `frontend/data/README.md`),
derived `frontend/src/data/world-countries.topo.json`, rebuild with `make fe-generate-world`, gate is
a CI step with `git diff --exit-code`. `topojson-server` is pinned to an exact version because the
output depends on it.
