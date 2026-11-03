---
paths:
  - "backend/app/**"
  - "backend/tests/fakes/**"
---
# Naming across the layers of a Python domain

> How a thing is named once `layers.md` has said where it lives. Where a project already has its
> own answer, the project wins.

## Modules

- A service module is named after its class without the `Service` suffix (`services/journey.py`
  → `JourneyService`).
- A port module is named after the port without the `Port` suffix: `refresh_token_repository.py`,
  `users_client.py`. The unit of work drops the domain prefix — `unit_of_work.py`, not
  `auth_unit_of_work.py` — because the package path already carries the domain.

## Ports, implementations and clients

**Every `Protocol` subclass is named with a `Port` suffix** (`SaltedHasherPort`,
`RefreshTokenRepositoryPort`); implementations drop it (`Argon2SaltedHasher`,
`RefreshTokenRepository`). The name alone says whether it is a contract or an implementation.

Give closely-related Protocols **distinct method names**, and say in each docstring that the name
differs on purpose: structural typing has no nominal check, so two ports sharing a signature can be
silently substituted.

An external API client carries the `Client` suffix (`ResendClient`). In a client or port class
name, `Transport` is reserved for `Protocol` roles (`EmailTransportPort`).

## Enums

**Every `Enum` subclass is named with an `Enum` suffix**, `StrEnum` and `IntEnum` included
(`TransportTypeEnum`, `UserRoleEnum`). The name alone says the value is one of a closed set, and
the bare noun stays free for an entity, value object or DTO of the same concept.

## Repository methods

`<verb>_<entity>[_<qualifier>]` — **the entity always appears in the name**:

```python
insert_challenge(challenge_entity)
find_active_challenge_for_update(user_id, challenge_type)
find_refresh_token_by_hash_for_update(token_hash)
revoke_all_active_refresh_tokens_by_user_id(user_id)   # plural for bulk
```

Not `find_by_hash_for_update(...)` — unqualified, it says nothing about what is being found and
cannot be grepped by entity. The apparent redundancy with the attribute name
(`uow.refresh_token_repository.find_refresh_token_by_hash_for_update`) is intentional: the
call site reads as a whole sentence.

**One exception: a generic port from the shared layer.** When a mechanic is reused across
entities (manual ordering, say), its port is a generic `Protocol` parametrised by a domain type
(`SortKeyRepositoryPort[ScopeT]`), and one base repository implements it for every model. Its
methods are named after the operation (`find_last_sort_key(scope)`), the domain port inherits
them with its own type argument, and the entity is named by that argument — not repeated in a
per-domain wrapper method. Re-declaring the methods with entity names would bring back exactly
the duplication the shared port exists to remove.

## Entity methods

The entity name appears in a method name only when the receiver is *not* that entity: a method
on the entity is bare (`refresh_token_entity.revoke()`, `UserEntity.create()`), a repository
method carries it.

## Variable layer suffixes

One concept exists as several types across layers, often in the same mapper function. Variables
and parameters holding a domain type carry a layer suffix:

- domain entity → `user_entity`, `refresh_token_entity`
- ORM model → `user_model`, `refresh_token_model`
- DTOs are usually unambiguous from their own type suffix; add one only on collision

Applies to locals **and** parameters, including repository/port/fake signatures:
`insert_refresh_token(refresh_token_entity=...)`.

This is a marker for *the layer of a domain concept*, not types-in-names generally — never
`count_int` or `name_str`.
