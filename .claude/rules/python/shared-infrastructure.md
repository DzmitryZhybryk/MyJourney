---
paths:
  - "backend/app/**"
  - "backend/tach.toml"
---

# Backend shared infrastructure (`backend/app/shared/`)

`shared/` is sliced by **vertical**: each technical integration is a self-contained package with its
lifecycle, clients, protocols and helpers. Before writing DB access, an HTTP client, email,
background tasks, JWT, hashing, pagination, manual ordering, logging, tracing or an exception base,
look in `shared/` and reuse what is there. Layer rules — `layers.md`; component vs `@cache`
factory — `component-lifecycle.md`; what a package's `__init__` exports and how to import from
it — `imports.md`.

- The component container is `infra/di/` (`BaseComponent`, `ComponentRegistry`, `run_components`);
  a pool-owning component to copy from — `infra/postgres/component.py`.
- A vertical declares its own `*Port` Protocols in its `ports.py` (`TaskBusPort`,
  `EmailTransportPort`, `SaltedHasherPort`), not in a domain's `application/ports/` — the one
  exception to `layers.md`.
- Hashing: passwords — `SaltedHasherPort`; a value looked up by index (refresh tokens) —
  `DeterministicHasherPort`.
- Keyset pagination: an endpoint's `*Request` / `*Response` extend `CursorPaginationFields` /
  `CursorPageFields[ItemT]`; the use case takes `PageQuery` and returns `CursorPage[ItemT]`;
  repositories use `decode_cursor` / `split_page`.
- Manual row order (`fractional_index/`): the domain supplies only a frozen scope dataclass and the
  `_sort_key_scope` hook of `BaseSortKeyRepository`; the model declares its own unique index over
  scope + `sort_key`.
- A domain repository subclasses `BaseDBRepository`; an external API client subclasses
  `BaseHTTPClient`.
- A stateless object is a `@cache` factory `get_<name>()` next to its class; a presentation
  dependency imports the factory, not the constructor.
- `app.shared.types` holds `DictStrAny` and the other aliases; use them instead of an inline
  `dict[str, Any]`.
- An entity's `updated_at` is touched through `TimestampedEntityMixin._mark_updated()`, not by
  hand-written `touch_*` / `mark_modified` methods.
- tach sees `app.shared` as one module, so the contract/implementation split of `imports.md` is
  guarded by `tests/unit/shared/test_import_hygiene.py`, which imports every `application`/`domain`
  module and the worker entrypoint in a clean interpreter.

## Exceptions

Raise a subclass of the `exceptions/base.py` class for the failure's `ErrorCategoryEnum` (one per
category), or of `InvariantViolationError` when our own code finds its assumption false. An
exception carries no HTTP status: category → status is decided only in `resolve_http_status`
(`exceptions/mappings.py`). `code` is an identifier in the external API contract — the frontend
maps it to text:

- once production exists, a `code` is stable — never rename or remove one;
- while there is no production (the same condition that lets the init migration be edited in
  place), a `code` may be renamed or removed, in the same change as the frontend that maps it.

## Patterns

- All DB work is async on psycopg3 (not asyncpg: procrastinate's atomic defer shares the SA
  connection).
- Dependency chain in `presentation/dependencies.py`: session → UnitOfWork → Service, in every
  domain, read-only ones included.
- A domain router mounts at `/v1/{domain}` in `create_app()` (`app/main.py`); operational
  endpoints (health) stay outside `/v1`.
- Deferring a task: outside a transaction `await task_bus.defer(task_name=..., ...)`; inside one
  `task_bus.bind_to(uow.session).defer(task_name=..., ...)` before `await uow.commit()` — one
  commit fixes the writes and the job.
