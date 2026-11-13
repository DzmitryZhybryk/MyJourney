---
paths:
  - "backend/app/shared/**"
  - "backend/app/main.py"
---
# Component lifecycle & composition root (Python)

## 1. The choice: managed component vs cached factory

Decide by one question: **is there anything to close on shutdown?**

| | Managed component | `@cache` factory |
|---|---|---|
| What goes here | connection pools (DB, HTTP), broker/worker apps, SMTP sessions — anything holding a socket, a thread, or a file handle | stateless, thread-safe objects: token services, hashers, serializers, validators |
| Why | it needs an explicit `shutdown`; without one, connections leak and graceful shutdown hangs | there is nothing to start and nothing to stop |
| Why a singleton at all | it owns the resource | recreating it per request is pointless work |

**Do not wrap a stateless object in a component.** Once a project has a DI container, the pull
to route everything through it is strong, and the result is classes with empty `startup`/
`shutdown` bodies — ceremony that hides which objects actually own a resource. A module-level
`@cache`d factory next to the class is the whole solution:

```python
@cache
def get_jwt_service() -> JWTService:
    """Process-wide singleton. Stateless and immutable, so per-request instances are waste."""
    return JWTService(...)
```

Testability does not justify a component either: override at the presentation seam
(`app.dependency_overrides` in FastAPI, or whatever the framework's equivalent is), not by
making the object lifecycle-managed.

## 2. Initialization order belongs to the composition root

One place — the app factory — builds components in dependency order and starts them. A
component that needs another one reads it from the registry during its own startup, which is
exactly what a plain cached factory cannot express: a factory knows nothing about ordering.

Ordering lives in the composition root, not in import side effects, and not in module-level
globals constructed at import time.

## 3. Use a class as the registry key

String keys erase types and collide silently. Keying by class keeps lookups typed:

```python
registry.get(SessionMaker)   # -> SessionMaker, not Any
```

When the natural key is a generic alias (`async_sessionmaker[AsyncSession]`), declare an empty
named subclass to serve as the key. It costs three lines and buys a readable, typed lookup.

## 4. Anti-patterns

- The registry reaching into `domain/` or `application/` → those layers depend on protocols,
  never on the container. Only the composition root and the presentation wiring touch it
- A `shutdown` that does not actually release (missing `dispose()` / `aclose()`) → the resource
  outlives the app in tests and reload cycles
