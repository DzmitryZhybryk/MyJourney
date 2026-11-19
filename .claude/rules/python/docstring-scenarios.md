---
paths:
  - "backend/app/**"
---
# Docstrings: the scenarios a function serves

A name says what a function does, not where it is needed. Every function or method with a
docstring carries a `Scenarios:` section — after the description, before `Args:` — with one line
per scenario it serves:

```python
def move(self, *, traveled_year: int, sort_key: str) -> None:
    """
    Ставит поездку на новое место: в другой год и/или на другую позицию внутри года.

    Scenarios:
        - перетаскивание поездки в ленте «Все путешествия»
        - правка поездки со сменой года: она встаёт в конец нового года

    Args:
        traveled_year: Год поездки
        sort_key: Место среди поездок этого года
    """
```

- A scenario is what a user does or what the system runs — registration, dragging a journey in the
  feed, the background send of a verification code — never the name of a calling function: grep
  finds callers, and a name goes stale on the first rename.
- Across a domain boundary and in shared code, a scenario is named by role, because a supplier never
  names its consumers: "a domain that stores city ids and shows their names", "any list with a
  manual order".
- A change that gives a function a new scenario adds its line in the same change; nothing else
  will.
- A method that implements a port does not repeat the section: the port's method holds it, and
  gets a docstring for it if it has none.
- No section on dunder methods, and none on route handlers: their docstring becomes the OpenAPI
  description.
