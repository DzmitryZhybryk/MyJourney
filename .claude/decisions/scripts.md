# Scripts

## A server-run command lives in `app/<domain>/scripts/`, a local-only tool in `devtools/`, both in git
- Why: a domain leaves for its own service together with its server commands; local tools (dataset
  builders) run on every new dataset version and carry rules (ru name arbitration) that must stay
  reproducible, but have no business in the production image.
- Rejected: keeping local-only tools out of git — they are rerun, not one-off, and the arbitration
  logic and its decisions file would be lost.
- Rejected: one shared `scripts/` folder for all domains — it would not move with its domain.
- Rejected: `procrastinate/__main__.py` into `shared/scripts/` — it is part of the queue vertical, not
  a standalone script.
- Source: PR #210, 2026-11-13

## Every script package is a tach module with its dependencies listed exactly
- Why: the listing makes each new link to app code visible in review, and declaring `devtools` as a
  module is what forbids `app` from importing it — such an import passes locally and crashes the
  production image, which ships without `devtools`.
- Rejected: `devtools` may import only `app.shared` — `storage_bootstrap` already needs the media S3
  client and the places builder needs `PlaceKindEnum`; a partial ban buys nothing.
- Rejected: dropping `devtools` from tach — loses the `app ↛ devtools` check above.
- Source: PR #210, 2026-11-13
