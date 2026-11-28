---
paths:
  - "backend/app/**"
  - "backend/tests/**"
---
# Imports

Where a name is imported from. Domain packages re-export nothing — `layers.md`.

## A `shared/` package: contract from the package, implementation from its module

A package's `__init__.py` re-exports only its contract: ports, exceptions, application DTOs, pure
functions and `get_<name>()` factories. Everything else — components, adapter classes, ORM models
and base repositories, HTTP schemas, middleware, handlers, framework dependencies — is imported from
the module that defines it:

```python
from app.shared.infra.procrastinate import TaskBusPort  # contract
from app.shared.infra.jwt.dependency import current_user_id_dependency  # implementation
```

Why: `application/` and `domain/` import the contract, so an implementation beside it would load
the web framework or the ORM into them. A module-boundary checker that sees the whole `shared`
package as one module cannot catch that; a test that imports each `shared` package alone and
asserts the framework modules are absent from `sys.modules` can.

## A type a port only annotates

A port module (`application/ports/*.py`, a vertical's `ports.py`) imports a type it uses only in
annotations (`AsyncSession`) under `if TYPE_CHECKING:`.
