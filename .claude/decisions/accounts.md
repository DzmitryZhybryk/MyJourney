# Accounts: auth and users

## auth stores email and username; users stores only the profile
- The profile is `display_name`, `terms_accepted_at`, `marketing_emails_consent`. Each domain
  serves its own part: `/v1/auth/me/` login data, `/v1/users/me/` the profile.
- `display_name` is required; registration passes `display_name = username` in
  `CreateUserRequest`, and users never sees the username.
- Why: both were stored twice, in `user_credentials` and `users`. auth needs them to log a person
  in; users does not.
- Rejected: a copy in each domain — two sources of truth for the same fields.
- Source: PR #146, 2026-10-07

## A valid token whose account no longer exists gets 401 `auth.account_not_found`
- Why: the token identifies nobody. On 401 the frontend's refresh fails (refresh tokens cascade
  with the credentials) and it logs out; `SESSION_INVALID_CODES` needs no change.
- Rejected: 404 `auth.user_credentials_not_found` (until 2026-10-12) — not a session-ending code,
  so a frontend consumer would keep the dead session.
- Source: PR #146, 2026-10-12

## Registration is one synchronous transaction across auth and users
- auth creates the credentials and calls users through `UsersClientPort` inside one
  `uow.transaction()`; users writes to the same session and does not commit.
- Why: both domains share one Postgres, so one transaction gives strict consistency for free.
- Rejected: creating the profile in a procrastinate task (atomic defer, outbox) — only the enqueue
  is atomic; a failed task does not roll registration back. That consistency window is justified
  only by separate databases.
- Rejected: a saga with compensation — undoing a successful registration of a logged-in user over a
  local INSERT is wrong; asynchronous creation rolls forward, not back.
- Revisit when: users moves to its own database or service. Then: an idempotent task
  (`INSERT … ON CONFLICT (user_id) DO NOTHING`) deferred atomically in the registration
  transaction, plus monitoring of failed jobs. Never a saga.
- Source: 2026-06-13

## A resend sends the same one-time code while it is live and extends its expiry
- A live code with attempts left is re-sent and its TTL restarts from this send; an expired one is
  burned and replaced. The resend cooldown counts from `last_sent_at`.
- Why: email arrives late or out of order (our retry queue, the mail path itself). With one code per
  challenge every letter in the inbox carries a working code. Industry model: Twilio Verify.
- Rejected: a new code on every resend (until 2026-11-03) — a delayed letter carries a burned code,
  and entering it costs an attempt on the new one.
- Rejected: several live codes per challenge (Okta) — breaks the one-active-challenge index, one
  check per live code on every attempt, guessing odds multiply by the number of codes.
- Rejected: fixing only our queue (the task checks the challenge before sending, cancel the pending
  job, skip the resend while a job is in flight) — leaves delays outside our queue.
- Source: stale verification code (#43), 2026-11-03

## One-time codes are stored encrypted, not hashed
- `SecretCipherPort` (Fernet, `CHALLENGE_CODE_ENCRYPTION_KEY`) for every challenge type; the send
  task gets the ciphertext and decrypts in the worker, so no plaintext code sits in the job table.
- Why: a code sent again must be read back, which a hash forbids. Encryption keeps a leaked database
  or backup useless without the key, and leaves each future code type free to pick its resend policy.
- Rejected: Argon2 hash (until 2026-11-03) — cannot resend the same code.
- Rejected: plain text — fine for email verification alone, wrong for future payment or 2FA codes
  in the same table.
- Rejected: AES-GCM / ChaCha20 from `cryptography.hazmat` — nonce uniqueness is on us; PyNaCl,
  pycryptodome, Tink — nothing gained over `cryptography`, or heavier.
- Revisit when: the key needs rotation — `MultiFernet` with the old and new key.
- Source: stale verification code (#43), 2026-11-03

## After exhausted attempts a new code waits until the old one expires
- Both send-verification and verify answer 429 `auth.challenge_attempts_exceeded` with
  `details.retry_after_seconds`; the exhausted check runs before the cooldown.
- Why: otherwise a resend hands out fresh attempts and the attempt limit is bypassed.
- Rejected: a new code right after exhaustion (until 2026-11-03) — five guesses per minute.
- Rejected: the `Retry-After` header — the frontend's `ApiError` reads only the body.
- Source: stale verification code (#43), 2026-11-03

## There is no generic `user_preferences` table
- A UI preference (language, theme) becomes a nullable column on `users`. A domain preference
  (e.g. travel interests) belongs to its own domain.
- Why: a separate table for one or two fields is not justified; a column on `users` is cheaper.
- Rejected: a generic preferences table — same reason.
- Revisit when: at least three independent mutable preferences exist.
- Source: i18n feature (DEV-22)

## Access has three independent axes: role, plan and email verification
- Role (`UserRoleEnum`: `user`/`admin`) is what you may do, plan (`UserPlanEnum`: `free`/`premium`) is
  what you pay for, `email_verified` already existed. Both enums and columns live in `auth`
  (`user_credentials.role`, `.plan`).
- Why: a plan expires with payment, a role does not, and an admin may be premium — one value cannot hold both.
- Rejected: one ladder `base < confirmed < premium < admin` — `confirmed` duplicates `email_verified`,
  and a ladder cannot express an admin on the free plan.
- Source: role model (#52), 2026-11-12

## Role, plan and expanded permissions travel in the access token; routes check permissions only
- `auth` expands role ∪ plan into a `permissions` list (`auth/domain/permissions.py`, the only copy of
  the map) and signs it into the token. A route declares `PermissionChecker("<permission>")`; it never
  reads role or plan. `plan` stays a claim only for future numeric limits a permission cannot express.
- Access TTL is 15 minutes: a demotion or an expired plan lives until the token expires.
- Why: no DB and no network on a guarded route — after the split every such check would otherwise be a
  call to `auth`. New roles, plan rights or per-user grants change only `auth`.
- Rejected: a DB lookup on guarded routes — a network call to `auth` per route after the split.
- Rejected: loading the user on every request with a `token_version` check (ai-recap) — a query on every
  click; the owner does not want it.
- Rejected: storing access tokens to revoke them — revocation needs a lookup per request, the same cost.
- Rejected: role in the token plus the map copied into `shared` — every service carries a copy, any role
  change redeploys all.
- Rejected: a separate `require_plan` guard — plan rights expand into permissions, one mechanism.
- Revisit when: the permission list reaches hundreds (header size) — then the token carries role + plan
  and services cache the map from `auth`; routes do not change.
- Source: role model (#52), 2026-11-12

## The `user` role has an empty permission set
- Login grants the base access (ownership checks cut off other people's rows); the maps list only what
  is granted on top.
- Why: a permission everyone holds checks nothing.
- Rejected: base permissions on `user` for ordinary actions — every route would check a right nobody lacks.
- Revisit when: a role below the base level appears (read-only, banned, guest) — then base actions get
  permissions.
- Source: role model (#52), 2026-11-12

## A missing permission is 403 `permission_required`; a malformed permissions claim is 401
- Every claim is required: an absent `permissions` claim, or one that is not a list of strings, is
  `invalid_access_token` 401 like any other broken claim; the frontend refreshes and gets a full token.
- Why: the route is public in openapi, and the frontend must tell "no right" from "no session" to
  refresh once and retry. A broken claim must be loud, not a quiet 403.
- Rejected: 404 like someone else's row — that rule hides a row's existence, a route is not secret.
- Rejected: an `auth.` prefix on the code — the prefix on `invalid_access_token` is a documented
  leftover; shared codes carry none.
- Source: role model (#52), 2026-11-12

## The first admin is made by a one-off script; every later role change goes through the admin UI
- Register through the UI, then `make set-admin-role email=…` / `make prod-set-admin-role email=…`
  (`app/auth/scripts/set_admin_role.py`). The script only grants admin and refuses once any admin
  exists. It uses no application code: raw SQL and shared settings only.
- Why: bootstrap is a one-time act and should not live in a product flow or bypass registration.
- Rejected: `ADMIN_EMAIL` granting the role on email verification — bootstrap logic living forever in a
  product flow.
- Rejected: an ai-recap-style seed creating the account from env email + password — a second
  account-creation path bypassing `auth` + `users` registration, a password in `.env`, a check on
  every start.
- Rejected: a CLI in `auth/presentation` calling services — presentation would assemble infrastructure.
- Rejected: a general set-role script with demotion — demotion belongs to the admin UI.
- The "no admin yet" guard is not a security boundary: whoever can exec into the container can run psql.
  Cost: if the only admin loses the account, recovery is psql.
- Source: role model (#52), 2026-11-13
