from typing import Any, cast

from app.shared.infra.di.exceptions import ComponentNotRegisteredError


class ComponentRegistry:
    """
    Позволяет типобезопасно работать с хранилищем компонентов инфраструктуры.
    В качестве ключа используется класс компонента, в качестве значения его экземпляр.
    """

    _store: dict[type[Any], Any]

    def __init__(self, store: dict[type[Any], Any] | None = None) -> None:
        if store is None:
            store = {}

        self._store = store

    def set[Component](self, *, key: type[Component], value: Component) -> None:
        self._store[key] = value

    def get[Component](self, key: type[Component]) -> Component:
        try:
            return cast(Component, self._store[key])
        except KeyError as err:
            raise ComponentNotRegisteredError(registry=type(self).__name__, key=key) from err

    def __contains__(self, key: type[Any]) -> bool:
        return key in self._store
