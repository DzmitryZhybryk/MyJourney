---
paths:
  - "backend/app/**"
  - "backend/tests/fakes/**"
---
# Layers of a Python domain

> Where each kind of code lives and which way it may depend, not a DDD tutorial. How what lives
> there is named — `naming.md`; what crosses a boundary — `dto.md`; reading soft-deleted rows —
> `soft-delete.md`. Where a project already has its own answer, the project wins.

## Layers

Each domain is self-contained:

- **`domain/`** — entities and value objects. Pure business logic, no infrastructure imports
- **`application/`** — use cases (`services/`), their inbound types (`schemas/`), outbound ports
  (`ports/`) and the domain's config type (`config.py`)
- **`infra/`** — ORM models plus the implementations of those ports
- **`presentation/`** — routes, HTTP schemas, dependencies

Inside `application/` each kind of thing has one place, and nothing else sits in the root:

```
application/
├── schemas/            inbound to the use case — split by ROLE
│   ├── commands.py     *Command
│   ├── results.py      *Result and the items nested in them
│   └── metadata.py     *Metadata — only where the domain has one
├── ports/              outbound from the use case — split by PORT
│   ├── <port>.py       one Protocol plus every type it declares
│   ├── tasks.py        names of tasks the domain defers — only where it defers any
│   └── unit_of_work.py where the domain has a store of its own
├── services/           the use cases — split by SERVICE
│   └── <service>.py    one *Service class, or a helper the services compose
└── config.py           *Config — only where the domain has tunables
```

No `__init__.py` re-exports: the import path names the role, the port or the service a type
belongs to (`schemas.commands.CreateJourneyCommand`, `ports.journey_repository.JourneyFilters`,
`services.journey.JourneyService`), and a re-exporting `__init__` is where the next dump forms.
A small domain gets the same packages — one layout everywhere is worth more than one file saved.

- **A helper that is not a use case** — a collaborator the services share or delegate to
  (`TokenIssuer`) — lives in `services/` beside them, under its own name. Presentation only
  constructs it; it never gets a package of its own. Pure logic with no dependencies goes to
  `shared/utils` when several domains need it; logic only one module needs stays a private
  function in that module.
- **Task names** are the contract between the use case that defers a task through the shared task
  bus and the `infra` handler registered under that name — the same `infra → application`
  direction as a port, so they live in `ports/tasks.py`.

Presentation schemas stay separate from application DTOs. What crosses each boundary, how it is
named and where it is converted — `dto.md`.

## Domain config

A service that needs tunables (TTLs, limits, cooldowns) declares them as constructor parameters:
one value — a plain parameter, several — a frozen `*Config` dataclass in `application/config.py`,
fields named without the domain prefix the class name already carries.

**`application` never imports the global settings object.** Mapping global settings onto the
domain's config is wiring: it happens in `presentation/dependencies.py`, next to the other
dependencies, and tests override that dependency. No `@cache` factory beside the config — building
a few scalars per request costs nothing, and a factory in `application` that reads settings is
exactly the import this rule forbids.

## Outbound ports (DIP)

Domain-specific outbound dependencies (repositories, unit of work, clients to other services)
are declared as `Protocol`, **one module per port** under `application/ports/`. `infra` imports
the port and implements it — **`infra → application`, never the reverse**. Services and test
fakes depend on the port.

- The module holds the Protocol **and every type the Protocol declares**: its `*Scope`,
  `*Filters`, `*Request` and read models (`dto.md` → "Port parameters"). A reader opening the
  port sees the whole contract. A type two ports of one domain both need lives with the port
  whose method declares it, and the other imports it from there — no `ports/common.py`.
- A port module imports only `domain`, `shared`, sibling ports and third-party types — never
  `schemas/`, `services/` or `infra` (a module-boundary checker such as tach enforces the last).

How a port, its module and its implementation are named — `naming.md`.

## Transaction boundary (UoW)

One use case = one transaction: `async with uow.transaction(): ... await uow.commit()`.
Rollback by default — leaving the block without an explicit commit rolls back.

**Every use case that touches its own store opens the block — reads included.** A read leaves
the block without `commit()`. One shape for every use case: a read on the bare session is not a
shortcut, it is a second convention. A use case whose only data comes from another domain has
nothing of its own to bound and opens no block.

**The commit belongs to the use case's entry point.** A cross-domain participant — another
domain's method the caller invokes *inside* its transaction so that both write atomically —
writes to the same request-scoped session and neither commits nor opens a block of its own;
everything lands in one atomic commit. Cross-domain wiring goes through the other domain's
`presentation`, never its `infra`.

**Another domain's use case the caller only reads from is called before the caller's block.**
It is an ordinary use case with a block of its own on the same request-scoped session, and
leaving that block rolls back whatever the caller's block still has pending.

## Repository read models

A query that returns a projection for a screen rather than an entity (aggregated or grouped
rows the database computed) returns a **read model**: a frozen dataclass in the port's own
module under `application/ports/`, declared next to the Protocol that returns it and built by
`infra`. Name it for what it is, with no suffix (`VisitedCity`), and compose it from domain
value objects where one fits.

If a row would equal an item of the use case's `*Result` field for field, the repository
returns that item type itself — a read model identical to the result item is only a place for
the two copies to drift. Keep a separate read model when the service reshapes the rows
(groups, merges, drops fields) before they leave the use case.

## Who builds a value object

Value objects are assembled in the application service; `Entity.create()` takes ready-made VOs
and mints identity internally. One exception: a VO that is the use case's own input type (a
`*Command` field typed as a domain VO) is built by the presentation adapter when it maps the
request into the command. The command then carries the domain type instead of a field-by-field
twin DTO.
