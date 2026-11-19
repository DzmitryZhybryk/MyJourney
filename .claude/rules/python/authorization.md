---
paths:
  - "backend/app/**"
---
# Authorization invariants (what a security review checks first)

Extends `common/security.md`.

- **The caller's identity comes only from the token.** A route gets `user_id` from
  `current_user_id_dependency`, never from the body, the path or a query parameter.
- **Ownership lives in the lookup itself.** A use case reads a user's row with a method that filters
  by owner (`find_journey_by_id_and_user_id`), never by id alone followed by a comparison in Python.
- **Someone else's row is "not found", not "forbidden".** No such row and a row owned by another
  user both raise the domain's `*NotFoundError` (404), so the response does not reveal that the id exists.
- **Every list query is scoped to the owner** (`*_by_user_id`).
- **Cross-domain clients pass ids, not trust.** A domain receiving an id from another domain
  (cities, users) re-checks it in its own store before writing it (`journeys.unknown_city`).
