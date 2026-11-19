---
paths:
  - "backend/app/**"
---
# Extracting part of a use case

A use case's body stays inline. A block leaves it on one of two grounds only:

- **The same knowledge in two or more places**, so the copies must change together
  (`JourneyService._find_route_points`). Extract every repeated block longer than one line; a
  repeated single line only when it is a rule of the domain (a normalisation, a formula, a
  threshold), and then into `domain/`. Copies that only look alike and change for different
  reasons stay apart: a helper that grows a flag or an `if` on its caller has merged two of those —
  inline it back.
- **A block used once that makes its own decision**: it branches, raises or computes, it is more
  than a couple of lines, and its name says what the code alone does not
  (`JourneyService._find_move_bounds`). This one is allowed, not required.

Not grounds, whatever the size of the block:

| The thought | The answer |
|---|---|
| "It's ten lines" | Lines are formatting. One call — a constructor, a field-by-field mapping, a log line — decides nothing and stays inline however long; an `if` around one such call is still one step |
| "It gets a name" | Only a name that adds something and is true of everything the helper does. `_build_city_location` restates `CityLocation(...)`; `_find_unverified_credentials` names a search the code does not make — it finds by id, then checks. `_build_*`, `_make_*`, `_prepare_*`, `_process_*`, `_handle_*` are names of the first kind |
| "A test can call it directly" | Tests go through the use case; a test is never the second caller |
| "The same `find` → `if None: raise` again" | That pair is the shape of every lookup, not knowledge, and stays inline however often it repeats. It joins a helper only together with more of the lookup's meaning, as a soft-deleted row treated as absent (`_find_user_journey_for_update`) |

The body keeps `uow.transaction()`, `commit()`, repository writes and deferred tasks, so a reader
sees everything the use case changes without leaving it. A lookup helper raises the not-found
error only — a soft-deleted row included (`_find_user_journey_for_update`) — and carries the owner
in its name when the lookup is owner-scoped. A check with an error of its own
(`ensure_not_verified` → `EmailAlreadyVerifiedError`) is a step of the use case and stays in the
body.

Where the block goes — the first row that fits:

| The block | Goes to |
|---|---|
| Reads only the data of domain objects | a method of their type in `domain/` (`GeoPoint.distance_km_to`) |
| Needs the service's dependencies; one service uses it | a private method of that service |
| Has dependencies of its own; several services use it | a collaborator in `services/` (`layers.md`, `TokenIssuer`) |
| Has no dependencies; one module uses it | a private module-level function in that module |
| Has no dependencies; several domains use it | `shared/utils` |
