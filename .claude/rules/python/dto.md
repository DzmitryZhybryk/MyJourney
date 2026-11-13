---
paths:
  - "backend/app/**"
---
# DTO conventions for layered Python services

> Stated in terms of boundaries, so it fits any layered service. Pairs with `layers.md` (layers,
> ports). Where a project already has its own answer, the project wins.

## Naming by boundary

| Boundary | Inbound | Outbound |
|---|---|---|
| our transport surface (HTTP handlers, consumers) | `*Request` | `*Response` |
| the use case (application service method) | `*Command`, or `*Metadata` for ambient request data | `*Result` |
| a call we make out (client to another service) | `*Request` | `*Response` |
| domain | no suffix | no suffix |

`*Request`/`*Response` repeat on two boundaries on purpose — the import path states the
direction, so there is no ambiguity. Prefer `<Verb><Noun>Command` (`CreateUserCommand`); it
disambiguates a command from an entity of the same name.

**The suffix marks the type that *is* the boundary** — on every boundary in the table: the
direct parameter or return value of the use case (`*Command`/`*Result`), the request body or
response model of a handler (`*Request`/`*Response`), the argument or return value of an
outbound call. Types nested inside it are named for what they are (`CitySearchItem`,
`MapCityVisit`, `IssuedRefreshToken`), not `*ResultItem` or `*ItemResponse`. A suffix on every
nested type stops carrying information: `MapCityResponse` inside `JourneysMapResponse` reads as
a second endpoint's response.

## One parameter, one role

A use case takes every value in one of four roles, and the role is decided by **where the value
arrived in the request** — never by what it seems to mean:

| Role | Arrives in | Parameter |
|---|---|---|
| **actor** — who is calling | `Authorization` header, auth cookie | plain: `user_id: UUID`, `refresh_secret: str` |
| **target** — which stored record is acted on | path | plain: `journey_id: UUID` |
| **payload** — what the action carries | body, query | one `*Command` |
| **metadata** — ambient request data | headers, connection | one `*Metadata` |

One parameter holds one role. `update_journey(*, user_id, journey_id, command)` says by its shape
that only what is inside `command` changes; `UpdateJourneyCommand(user_id, journey_id, origin, …)`
leaves the reader guessing whether the ids are being changed too.

- **Payload is always a command, even with one field** (`VerifyEmailCommand(code)`). A loose
  `code: str` next to `user_id: UUID` is exactly the ambiguity the roles exist to remove. No
  payload — no command: `delete_journey(*, user_id, journey_id)`, `logout(refresh_secret)`.
- **A secret is classified by its channel, like everything else.** A password or a one-time code
  in the body is payload and sits in the command; a refresh secret from the auth cookie is actor
  and stays a plain parameter. Asking "is it a credential?" gives the wrong answer both ways.
- **An id in the body is payload.** `CreateUserCommand.user_id` is the id of the record being
  created, arriving in the body of an inter-domain request — it stays in the command. The actor
  is whoever the token says.
- **The output is always a `*Result`, even with one field** (`JourneyDistanceResult`).

## Port parameters: the key stays loose, the rest is grouped

The same idea at the outbound boundary. A port method (repository, client) takes:

- **the key named in the method** (`_by_user_id`, `_by_id_and_user_id`) as plain arguments;
- **everything else grouped by role** into a frozen dataclass, from a closed vocabulary:

| Type | What it is | Example |
|---|---|---|
| `*Scope` | the set of rows the operation works within; required | `JourneyOrderScope(user_id, traveled_year)` |
| `*Filters` | an optional narrowing of a list, chosen by the caller | `JourneyFilters(year_from, year_to, transport_types)` |
| `*Request` | what we send to another domain or service | `CreateUserRequest` |
| `PageQuery` | paging, from the shared layer | — |

`*Params`, `*Criteria`, `*Args` and `*Context` are not in the vocabulary: a bag named for its
shape says nothing about its role, and a second synonym for `*Filters` is where two conventions
start.

**Three loose values are the signal.** When a method takes three or more values that are neither
the key nor an already-grouped object, a concept is hiding in the signature — name it. The count
is a smell, not a quota: `find_journeys_page_by_user_id(user_id, page, filters)` has zero loose
values and is right as it is, while `create_user(user_id, display_name, consent, accepted_at)`
hides a `CreateUserRequest`.

- A single value is not wrapped.
- A port object never mirrors a `*Command` field for field — pass the key and the command's
  already-grouped parts instead.
- A `*Scope` or `*Filters` may itself be a field of a `*Command` (`ListJourneysCommand.filters`),
  the way a domain VO is: the use case hands it straight to the port.

## One type per boundary, even when the fields match

A type never crosses two boundaries: the transport schema does not reach the service, the
command does not reach the wire. When an outbound client sends exactly the fields the target's
own command declares, **still declare your own type** on the caller's side. It pins the set of
fields you actually send, and it is what lets the callee's schema change without reaching into
your code — the same property you would need the day that call becomes a network hop.

The cost is a mapping function per boundary. That is the price of the boundary, not an
accident of it — if the duplication feels wasteful, the question to ask is whether the boundary
should exist, not whether to share the type across it.

## pydantic vs dataclass

> Pydantic only when there is something to validate or carry semantically. Otherwise
> `@dataclass(frozen=True, slots=True)`.

"Something to validate or carry" means: semantic types (`EmailStr`, `SecretStr`, `HttpUrl`,
custom validators), parsing from an untrusted source (HTTP body, external API, queue), or
participation in OpenAPI. Conversion at the boundary stays one line either way:
`Schema.model_validate(obj, from_attributes=True)`.

Applies to **transport objects only**. Not to transport schemas (always pydantic — it is the
system boundary), not to entities or value objects (they carry behavior and invariants, so they
are plain classes).

## Immutable by default

Transport objects are frozen: `@dataclass(frozen=True, slots=True)` or
`model_config = ConfigDict(frozen=True)`. Outbound HTTP response schemas are frozen the same way.

**A collection's type is chosen by what the data means**, on every outbound type — application
DTOs, read models, port and repository return types, and response schemas:

| The data is | Type |
|---|---|
| an ordered sequence nobody changes after building it | `tuple[T, ...]` |
| a set of distinct values whose order means nothing | `frozenset[T]` |
| ordered **and** distinct (years ascending, ranked ids) | `tuple[T, ...]` — Python has no ordered set; the source guarantees uniqueness (`DISTINCT`, a `set` before sorting) and the docstring states it |
| being built right now, inside one function | `list[T]` — local only, converted before it leaves |

`list` in a signature or a field is the type that needs a reason. Whether it would serialize the
same is not the question — `tuple` and `list` render as the same JSON array, and that is exactly
why the choice costs the contract nothing.

| The reason it gets skipped | Why it still applies |
|---|---|
| "The neighbouring schemas all use `list`" | Neighbours written by habit are not a convention. Change the module you are in, not only the new line |
| "It's serialized immediately, nobody can mutate it" | The type also documents meaning — `frozenset` says "no order, no repeats" where `list` says nothing |
| "`set` guarantees uniqueness, use it for ordered data" | A set drops the order; serialization then follows hash iteration order, which is not a contract |

Two exceptions, both narrow:

- **Inbound transport schemas** need not be frozen — the framework constructs them and they die
  with the handler
- A **mutable local accumulator** (built during a fold, converted to a frozen type before it is
  returned) is legitimate — but say so in its docstring, since a non-frozen transport object
  otherwise reads as an oversight

## Where validation happens

**Everything the request can check by itself is checked in the request schema.** That covers
form (presence, length, range, pattern), relationships between fields of the same payload
(`year_from <= year_to`, `origin != destination`) and comparisons with the current time
("the year is not in the future") — field constraints plus a `model_validator`. Do not move such
a check inward, and do not add a domain method, value object or service branch whose only job is
to re-check what the schema could have rejected.

What stays inward is only what the payload cannot answer on its own: rules that need stored
state (does the place exist, is the email taken, is this row the caller's) or another service.

An entity check earns its place only when it runs on **every** construction of the object,
including rows read back from the database — then it guards the data the entity holds, and a
failure signals corrupted data, not a bad request. A check that runs only in the factory for a
new record (`Entity.create`) protects nothing once the record exists: it is an input check, and
it belongs in the request schema. Request parameters that are not part of any entity (filters,
sorting, paging) never get a domain type for the sake of validation either: a value object around
a filter carries no domain meaning, only a second copy of a schema check.

A schema check fails with the generic validation error (one shared code for every such
failure). When the client needs to branch on one particular rule, raise a coded exception from
inside the validator: pydantic v2 wraps only `ValueError`, `AssertionError` and
`PydanticCustomError`, so any other exception propagates untouched to the app's error handler
with its own code. Without that need, the generic error is the right answer — a client that
builds the request itself should not be producing it.

## Wire casing in exactly one place

If the wire format differs from Python's casing, declare it **once** in a base model at the
transport boundary (`alias_generator`) and let every schema inherit. Everything inward of that
base stays `snake_case` — DTOs, domain, storage. One class is the entire answer to "how is this
serialized", and adding a schema requires no decision.

## Who owns the mapping

The adapter that owns the **outer** type owns the conversion — the transport layer builds the
command and renders the result. The use case never imports a transport schema; that import
direction is what keeps the application layer reusable behind a second transport.

The two directions do not look alike, and should not:

- **Inbound** — pass actor and target as plain arguments taken from the token and the path, and
  construct the command explicitly, field by field, from the body and query only. It is the
  checkpoint where a renamed or newly added transport field must be consciously admitted inward
- **Outbound** — one line: `Response.model_validate(result_item, from_attributes=True)`. There is
  nothing to guard, and a hand-written mapper here is just a place for a field to go missing
