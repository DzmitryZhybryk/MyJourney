---
paths:
  - "backend/**/*.py"
---
# Python coding style

Extends `common/coding-style.md`. Layers — `layers.md`; names across layers — `naming.md`;
transfer objects and collection types — `dto.md`.

## Toolchain

The linter, formatter, import sorter and type checker are whatever `pyproject.toml` configures,
one tool per job. Do not add a second tool beside it (Black or isort beside ruff, mypy beside ty).

## Docstrings

Google style, written in Russian, with `Args:` and `Returns:` sections:

```python
def get_log_level_for_exception(exc: Exception) -> int:
    """
    Определяет уровень логирования на основе типа исключения.

    Args:
        exc: Исключение

    Returns:
        Уровень логирования (logging.ERROR, logging.WARNING и т.д.)
    """
```

Keep them short and in plain language. A comment or docstring carries what the code does not show,
not a retelling of the decision, its history or metrics.

- Comments and docstrings name no domains, modules or files from elsewhere in the project; describe
  them by role ("the calling domain"). A supplier domain never names its consumers, not even in a
  docstring.

## Named arguments

**Call side:** pass every argument as a keyword.

```python
Password(hash=user_credentials_model.password_hash)   # not Password(user_credentials_model.password_hash)
```

**Declaration side:** a function, method or constructor with **more than one** parameter makes them
all keyword-only with `*`. A single parameter may stay positional. `self` / `cls` do not count.

```python
def decode_cursor(*, cursor: str, parsers: Sequence[CursorParser]) -> tuple[object, ...]: ...
def find_journey_years_by_user_id(self, user_id: UUID) -> tuple[int, ...]: ...
```

Exempt only signatures that something else calls **positionally**: framework hooks (pydantic
validators, Starlette exception handlers and middleware `dispatch`, procrastinate `pass_context`
tasks), pytest test functions and fixtures (fakes and helpers under `tests/` still follow the rule),
dunder protocol methods (`__eq__`, `__aexit__`; `__init__` is **not** exempt), callbacks passed to
`map` / `sorted` / `key=`, and `Protocol` methods mirroring a third-party API.

## `Self` and blank lines

- Use `typing.Self` for a method that returns its own instance, not a string literal.
- Leave a blank line after a closing `if` block or `for` loop before the next statement:

```python
if exc.category is ErrorCategoryEnum.INTERNAL:
    return logging.ERROR

return default_handler
```

## Recurring shapes

- Do **not** alias a repository (`repository = self._uow.x_repository`); always call
  `self._uow.x_repository.method(...)` directly.
- A single-row `find` in a repository ends with a ternary `self._to_entity(...) if model else None`,
  not an early return. Before adding a method to a layer, grep its neighbours and repeat their shape.
