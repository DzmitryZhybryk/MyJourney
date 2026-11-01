# Domains: keeping them separable

## No foreign keys between domains
- A column that points into another domain (`journeys.user_id`, the city ids from geo) is a plain
  uuid. Foreign keys stay inside one domain (auth → `user_credentials`).
- The receiving domain checks a foreign id through the other domain's client before writing it
  (`journeys.unknown_city`).
- Why: every domain must be extractable into its own service and database without a redesign.
- Rejected: foreign keys across domains — they tie two domains' tables to one database.
- Source: journeys design; auth and users already followed it

## An `AppError` knows nothing about HTTP
- An `AppError` carries an `ErrorCategoryEnum`; the HTTP status is chosen only in the HTTP adapter
  (`resolve_http_status`).
- Why: the transport is HTTP today and may be a queue, gRPC or a CLI tomorrow; an HTTP status on an
  exception leaks HTTP into the domain. The owner wants maximum flexibility and clean layers.
- Rejected: `status_code` on the exception — same reason.
- Source: PR #14, 2026-05-24
