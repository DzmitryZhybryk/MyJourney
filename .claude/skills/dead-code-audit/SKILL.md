---
name: dead-code-audit
description: Use when asked to find or remove dead code, unused functions, exports, files or dependencies in backend/ or frontend/.
---

# Dead-code audit

```bash
cd backend && make dead-code                             # vulture: unused functions/classes (config in pyproject.toml)
cd backend && uv run ruff check . --select F401,ERA      # unused imports + commented-out code
cd frontend && npx knip                                  # unused files, exports, dependencies
cd frontend && npx ts-prune                              # unused TS exports
cd frontend && npx depcheck                              # unused npm dependencies
```

- A false positive from vulture (dynamic imports, FastAPI routes) goes into
  `backend/vulture_whitelist.py`; never lower `min_confidence` to hide it.
- Remove in batches: dependencies first, then exports, then files, running the tests after each
  batch. Commit once the cleanup is finished (the `git-workflow` skill covers the commit).
