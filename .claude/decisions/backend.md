# Backend process: cross-cutting choices

## Settings are one import-time singleton
- `app.shared.settings` builds `settings` (`get_app_settings()`) when first imported; entrypoints, components and
  presentation dependencies read it directly. Domain tunables still reach `application` only as a `*Config` built in
  `presentation/dependencies.py` (`layers.md`, "Domain config").
- Why: one process, one source of configuration. Tests never vary the global — unit tests build `*Settings` sub-models
  and `*Config` through constructors, api tests override the presentation dependency.
- Rejected: `Settings` built in the entrypoint and threaded through `create_app(settings=...)`, the component registry
  and a `settings_dependency` (the ai-recap pattern) — it solves per-test settings variation, which this project already
  gets from constructors, and costs a `Settings()` at every entrypoint, a `Depends(settings_dependency)` in every
  dependency that needs one field, and a second settings object whenever a factory reads the environment itself.
- Revisit when: a test must vary a setting that no `*Settings`/`*Config` constructor reaches, or two apps with different
  settings share one process.
- Source: plan D review, 2026-10-24

## The backend version is static in `[project].version`
- The version is bumped by hand in the feature's commit (skill `git-workflow`); the app reads it from the installed
  package's metadata (`importlib.metadata.version`).
- Why: one source, visible in the diff of the change that earns it.
- Rejected: `hatch-vcs` (version from the git tag) — the `backend-vX.Y.Z` tag goes on `main` after the merge, so a
  feature branch would carry `X.Y.Z.devN+g…` and the bump rule would disappear.
- Source: PR #175, 2026-10-28

## Schema names in `openapi.json` are not part of the versioned contract
- Renaming a component (`LanguageEnum`, `TransportTypeEnum`, `MovePlacementEnum`) with the wire values unchanged is
  a patch bump; the regenerated `frontend/src/api/generated/` lands in the same commit (`codegen-contract.md`).
- Why: the backend version tracks what an HTTP client observes — routes, payload shapes, wire values, error `code`s.
  A component name is a label inside the schema document; the only consumer that depends on it is the frontend SDK,
  which is regenerated in the same commit.
- Rejected: major bump — treats every generator-visible rename as breaking while no client outside this repo generates
  code from `openapi.json`.
- Revisit when: a client outside this repo generates code from `openapi.json`.
- Source: PR #172, 2026-10-28

## `info.version` in the `openapi.json` snapshot is a constant, not the package version
- The snapshot test (`test_openapi_schema.py`, `_SNAPSHOT_VERSION`) replaces `info.version` before comparing and
  before writing the file through `make openapi-dump`. The running app still reports the package version in its
  live schema and `/docs`.
- Why: the committed file is the codegen input of the frontend SDK, and the generator ignores `info.version`; with
  the real version every backend bump rewrote `openapi.json` without a contract change.
- Rejected: the real version in the snapshot (until 2026-10-30) — every bump turned the snapshot gate red and added
  an `openapi.json` diff to a commit that did not touch the API.
- Rejected: no `version` passed to `FastAPI` — OpenAPI requires `info.version`, so FastAPI fills in `0.1.0`, a
  misleading number in `/docs`.
- Revisit when: a client outside this repo generates code from or reads `openapi.json`.
- Source: PR #176, 2026-10-30

## The exception tree branches by reaction (`ErrorCategoryEnum`) under one root, `AppError`
- A failure subclasses the category class for its reaction; a family (`ObjectStorageError`) or a layer is not a level
  of the tree. Every leaf declares its own `code` and codes are unique — guarded by `tests/unit/shared/exceptions/test_codes.py`.
- Why: the category is the only axis anything branches on — HTTP status and log level. Nothing catches by origin or
  layer, and `category` is a class attribute that works wherever the class sits.
- Rejected: `Internal`/`External` at the top, `External` split into temporary/persistent — nothing catches `External`;
  a temporary failure is not only external (exhausted pool, deadlock); a use case may translate a dependency failure
  into a 4xx.
- Rejected: one node per layer (`DomainError`/`RepositoryError`/`ServiceError`) — the layer is visible in the
  traceback, the node carries nothing to read, and the boundary blurs (a business rule checked in a service).
- Rejected: `Result` objects for business errors — no gain over exceptions in a web service; `find_* -> Entity | None`
  already covers an expected absence.
- Rejected: root named `BaseDomainError` (until 2026-11-01) — the root also covers DI, S3 and pagination, and the
  name kept raising the question whether the tree is right.
- Source: exception hierarchy review, 2026-10-31

## A false assumption of our own code raises `InvariantViolationError`, outside the `AppError` tree
- Its subclasses carry no category and no `code`; their data goes into the message text. HTTP answers the generic
  500 `internal`, the log gets ERROR with a traceback.
- Why: the reaction is an alert and an investigation, not a client contract. A `code` would publish a bug as an API
  identifier, and the message would leak internals through the error envelope.
- Rejected: a subclass of `InternalError` with its own `code` (until 2026-11-01) — same reason.
- Rejected: one base for invariant violations and the persistent failures of adapters — a base defined by a missing
  trait has nothing to read, and a family whose temporary leaf needs a category (503, retry) would split across two roots.
- Rejected: the criterion "does not reach the client" or "has no `code`" — every failure reaches the client as a 500,
  and such a class would absorb adapter failures with a different reaction (retry, provider config, not a code fix).
- Rejected: `AssertionError` as the base — accurate in meaning, misleading in a traceback.
- Source: exception hierarchy review, 2026-10-31

## Log lines of one request are joined by the OpenTelemetry trace context, not an own request id
- The API gives FastAPI's native telemetry a `TracerProvider` without an exporter (`app.shared.infra.telemetry`); a
  structlog processor writes `trace_id`/`span_id` of the current span into every line written during a request.
- Why: FastAPI already opens a span per request and continues an incoming W3C `traceparent`; the same id will join the
  logs to exported traces and to a frontend trace.
- Rejected: an own `request_id` (uuid in middleware, `X-Request-ID`) — a second correlation mechanism beside the one
  FastAPI ships, and it joins no trace.
- Revisit when: traces are exported — the provider then owns a span processor and becomes a component with shutdown.
- Source: logging audit, 2026-11-02

## A handled error reaches the request log line through the request scope; only the logging middleware writes it
- An exception handler answers the client and hands the exception and its `code` to `remember_handled_error`; the
  pure-ASGI `HTTPLoggingMiddleware` writes one line per request — type, code and, at ERROR, the traceback. An
  unhandled exception is logged by the middleware and re-raised.
- Why: the handler answers before the request returns to the middleware; without the hand-over the line knew only
  the status, and an INTERNAL error was logged as a bare 500. One writer keeps one line per request with its context.
- Rejected: logging in the handler — two lines per error, and the handler's line has no request fields.
- Rejected: re-raising INTERNAL from the handler — the next reader "fixes" a handler that raises instead of answering;
  the error would go through `ServerErrorMiddleware`, which re-raises to the server after answering.
- Rejected: FastAPI's native telemetry logs instead of the middleware — they record only unhandled exceptions and
  validation failures, never a handled `AppError`, write no line per request, and need an OTLP log pipeline.
- Rejected: `BaseHTTPMiddleware` as the base — it runs the app in a separate task, so context bound deeper in the
  request (`user_id`) never reaches the line.
- Source: logging audit, 2026-11-02

## An incoming `traceparent` is accepted at the edge
- `ops/Caddyfile` passes `traceparent`/`tracestate` to the API, so a request's trace may start in the client.
- The client's sampled flag is ignored: the provider samples every request (`ALWAYS_ON`).
- Why: a frontend trace joins the backend's through this header. A client-chosen id only groups that client's own
  lines: the format is validated and our ids are not exposed.
- Rejected: stripping the headers in Caddy (proposed 2026-11-02) — closes front-to-back tracing for no real protection.
- Rejected: honouring the sampled flag (until 2026-11-02) — an unsampled span is not recorded, so a client's `-00`
  dropped `route` from the request log line.
- Revisit when: traces are exported — decide whether the client's sampled flag may switch tracing of its requests.
- Source: logging audit, 2026-11-02

## Integration tests run each in its own event loop; the Postgres schema is created synchronously
- The async engine is function-scoped (`db_engine` in `tests/integration/conftest.py`); the schema is built once
  per session by a sync `create_all`. `asyncio_default_fixture_loop_scope = "function"`: an async fixture wider
  than a function declares its `loop_scope` explicitly and hands out only data, never a loop-bound object
  (`media_storage_settings`).
- Why: an async psycopg connection is bound to the loop it was opened in; a shared loop lets a task leaked by one
  test live into the next.
- Rejected: building the schema with an async engine in a session-loop fixture, for symmetry with RustFS — the
  RustFS fixture is async because it reuses the dev stack's async `bootstrap_buckets`; Postgres has no such code.
- Rejected: one async engine per session with tests in the session loop — weaker isolation and two loop
  conventions in one suite, for a speed-up nobody measured.
- Revisit when: integration time becomes a bottleneck and a measurement shows engine setup is the cost.
- Source: integration harness review, 2026-11-02
