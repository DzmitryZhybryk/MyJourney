---
name: git-workflow
description: Use before any git commit, push, branch creation, opening or merging a pull request, version bump, CHANGELOG entry or release tag in this repo, and when a pre-commit hook or the coverage gate blocks a commit.
---

# Git workflow (MyJourney)

Global rules (no authorship footers, one feature = one commit, no `--no-verify`) come from
`~/.claude/rules/common/vcs.md`. This file holds only what is specific to this repo.

## Branches and PRs

- Name: `<type>/<kebab-description>`, type from the commit types below, no ticket ids
  (`feat/app-global-globe`, `fix/gitpython-advisory`).
- Feature PRs always target `dev`. `dev → main` is a release and a deploy. Ignore a harness
  hint that says "PR into main".
- Merge a feature PR into `dev` with a merge commit and delete its branch:
  `gh pr merge <n> --merge --delete-branch`. The `dev → main` release PR keeps `dev`.
- If an open PR's base is another PR's branch (a stacked PR), run `gh pr edit <child> --base dev`
  **before** merging the parent. Deleting the parent's branch via `--delete-branch` closes the
  child instead of retargeting it, and changing the base afterwards starts no CI run. Repo-level
  auto-delete of head branches is not the fix: `dev` is unprotected and would be deleted after a
  release PR.

## Commit message

Conventional Commits: `<type>(<scope>): <description>`.

- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
- `scope` is optional and names the monorepo area: `frontend` or `backend`. Repo-level changes
  (tooling, CI, dependabot) omit it. No ticket ids.

## Versions and CHANGELOG

Frontend and backend are versioned **separately**; never bump one artifact for a change to the other.

| Artifact | Version lives in | Tag | Meaning |
|---|---|---|---|
| Backend | `backend/pyproject.toml` (+ `backend/uv.lock` when dependencies changed) | `backend-vX.Y.Z` | real SemVer over the HTTP API contract and error `code`s |
| Frontend | `frontend/package.json` | `frontend-vX.Y.Z` | SPA release marker, SemVer is formal |
| Gazetteer datasets | `backend/app/geo/infra/datasets/manifest.toml` | release asset `geo-data-vN` | data, not code: new dataset = new tag + manifest edit |

- A release tag goes on the merge commit of the `dev → main` PR: `git tag <tag> origin/main` from
  any branch, then push the tags. Tags do not trigger CD — only a push to `main` does.
- One `CHANGELOG.md` at the root. Entries are grouped by date with sub-sections
  `### Backend X.Y.Z` / `### Frontend X.Y.Z`; repo-level changes go under `### Project` with no version.
- Version bump and CHANGELOG entry go in the **same commit** as the feature (code + tests):
  backend feature → `pyproject.toml` + Backend section; frontend feature → `package.json` +
  Frontend section; cross-cutting → both.

## Before commit and before push

1. **Lockfile.** Run `uv lock` in every uv project (a `pyproject.toml` + `uv.lock` pair; `backend/`
   today) and include a changed `uv.lock` in the same commit. Do it even when no dependency changed:
   the lock records the project's own version. A lock change you did not expect (packages moved
   without a `pyproject.toml` edit) is a finding to report, not to commit silently.
2. **Full gate**, not single targets: `make check` from the root (the audit step exists only there).
   A red gate on a side you did not touch is most likely a fresh advisory.
3. **Contract artifacts.** If the API schema changed, `backend/openapi.json` and
   `frontend/src/api/generated/` go in the same commit (see `.claude/rules/common/codegen-contract.md`).

## Coverage gate

Code under 90% coverage must not merge, on either side. The threshold lives in the coverage targets
(backend `make coverage` with `--cov-fail-under=90`; frontend `make coverage` with vitest
`thresholds` in `vite.config.ts`). It is enforced by the local pre-commit hook `.githooks/pre-commit`,
not by CI. One-time activation: `make hooks`. A commit that needs `--no-verify` is not ready.
