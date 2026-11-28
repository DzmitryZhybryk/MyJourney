---
paths:
  - "backend/app/**"
---
# Where input is validated

A value a client sends is one of two kinds, each judged in one place:

1. **A choice** (a limit, a filter, a setting) can only be malformed, never false. Judged in the
   **request schema** (server-side) and nowhere else: form, ranges, cross-field rules of one
   payload, comparisons with the current time.
2. **A claim about a fact the server can observe** (a file's size, type or content; that a row
   exists or is the caller's) can be false while well-formed. The schema only rejects garbage; the
   use case **decides from the observed fact** — what storage reports, what decoding finds, the
   owner-scoped lookup. A signed URL narrows the client but replaces no check.

**A type also read back from storage carries the shape only** — fields, types, enums, required.
Limits on what a writer may submit live in that writer's request schema; a writer without one (a
seed file) is covered by a test that feeds its data through that schema.

| The thought | The answer |
|---|---|
| "One schema for request, seed and storage read" | Forbidden: limits in two places |
| "Can't trust the client, recheck on read" | The schema is server-side. Recheck facts, not choices |
| "A migration could write a bad row" | Our writers get a test, not a copy of the limits |

An entity check belongs only where it runs on every construction, rows read back included; one
only in `Entity.create` is an input check. Filters and paging get no domain type for validation.

For a rule the client must branch on, raise a coded exception in the validator: pydantic wraps
only `ValueError`/`AssertionError`/`PydanticCustomError`, others keep their own code.
