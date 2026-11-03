---
paths:
  - "backend/tests/**"
---
# Backend tests: philosophy and style

How a test is written. Where it lives, markers, fixture placement and run targets are the
project's own layout rule (`testing-layout.md`).

## Classicist, with hand-written fakes

- **State-based, not interaction-based.** Assert on the resulting state or return value, never on
  call order. Use real objects where they are cheap: domain entities, stateless infra
  (`JWTService`, `TokenIssuer`), real hashers inside their own roundtrip test.
- **Fake only the I/O boundary:** the outbound ports (repositories, UoW, clients, task bus, email
  transport).
- **Constructor DI.** Application services are unit-tested by passing fakes directly, bypassing
  the web framework. `dependency_overrides` belong to the **api** level only.

### Fakes over mocks

- Hand-written in-memory fakes live in `tests/fakes/`, each subclassing its port: a repository
  backed by a `dict`, a client or task bus recording its calls in a list. They survive refactors
  and read like scenarios (`find` after `insert` returns it).
- `AsyncMock` only where a fake has nothing to record but the call itself — the fake UoW's
  `commit_mock` / `flush_mock`.
- Never mock `AsyncSession` / SQLAlchemy.
- Design a fake as a full replacement of its port, not a one-off stub: the same fakes serve the
  api level through `app.dependency_overrides`.

### Thin Protocols keep fakes honest

A port declares only the methods in use; the real class and the fake both subclass it, so the type
checker catches drift. Port rules — `layers.md`.

## Determinism

- **Time:** construct entities with explicit timestamps (`expires_at`, `revoked_at` are constructor
  arguments). For a method that stamps *now* (`revoke()`), assert the field is set, not its value.
  Never freeze time globally and never inject a `Clock` into production code for tests.
- **Randomness** (`secrets.token_urlsafe`): never predict the value; assert the invariant
  (`entity.token_hash == hasher.digest(plaintext)`).
- **Slow primitives** (a password hash tuned to tens of milliseconds): service tests use a fake
  hasher; the real one is covered once, in its own roundtrip test.
- **No sleeps:** wait for the condition, not a duration.

## Test data builders

Plain functions with keyword defaults in `tests/builders.py`
(`make_refresh_token(*, expires_at=..., revoked_at=None)`). No `factory-boy`, no `faker` —
determinism beats realism.

## Reuse before create

Before adding a test, fixture, fake, builder or helper, enumerate what exists and reuse it. A
near-duplicate is the same defect as copy-pasted production code.

```bash
grep -rn "@pytest.fixture" tests
grep -rn "^def make_\|^class Fake" tests/builders.py tests/fakes
```

Read only the matching definitions, then reuse by name.

- **No file-local `_make_*` helpers.** Build the object inline in the test, or use the shared
  builder or fixture. A helper is justified only once the same construction repeats across files,
  and then it becomes a builder or fixture, not a file-local function.

## Conventions

- Flat functions, **no test classes**. Group by naming (`test_login_*`) and subset with `-k login`.
- A helper class one test needs (a provider subclass, a stub type) is declared inside that test, as
  part of its arrange step; one the whole file shares goes right after the imports. Never between tests.
- `asyncio_mode = "auto"`: write `async def test_...` with no decorator.
- Name: `test_<unit>_<condition>_<expected>`, plus a **one-line Russian docstring** stating what is asserted.
- Variants through `@pytest.mark.parametrize`; `pytest.raises(SomeError, match=...)` where the
  message is the signal.
