# Domains: keeping them separable

## No foreign keys between domains
- A column that points into another domain (`journeys.user_id`, the city ids from geo) is a plain
  uuid. Foreign keys stay inside one domain (auth → `user_credentials`).
- The receiving domain checks a foreign id through the other domain's client before writing it
  (`journeys.unknown_city`).
- Why: every domain must be extractable into its own service and database without a redesign.
- Rejected: foreign keys across domains — they tie two domains' tables to one database.
- Source: journeys design; auth and users already followed it

## PUT answers 204 with no body; PATCH answers with the changed resource
- A client that needs the state after a PUT reads it again (`GET`).
- Why: why not recorded — it is the pattern the routes already followed (`PUT /v1/journeys/{id}/`,
  `PATCH /v1/users/me/`); the owner made it the rule.
- Rejected: a PUT returning the saved resource.
- Source: #51, 2026-11-21

## An `AppError` knows nothing about HTTP
- An `AppError` carries an `ErrorCategoryEnum`; the HTTP status is chosen only in the HTTP adapter
  (`resolve_http_status`).
- Why: the transport is HTTP today and may be a queue, gRPC or a CLI tomorrow; an HTTP status on an
  exception leaks HTTP into the domain. The owner wants maximum flexibility and clean layers.
- Rejected: `status_code` on the exception — same reason.
- Source: PR #14, 2026-05-24
