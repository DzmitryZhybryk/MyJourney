"""
Unit-тесты ``ComponentRegistry`` — типобезопасного хранилища компонентов по ключу-классу.

Покрывают set/get round-trip, перезапись, ``__contains__`` и ошибку незарегистрированного
ключа (``ComponentNotRegisteredError`` — нарушенный инвариант композиционного корня).
"""

import pytest

from app.shared.infra.di.exceptions import ComponentNotRegisteredError
from app.shared.infra.di.registry import ComponentRegistry


class _ComponentA:
    """Ключ-тип компонента для тестов registry."""


def test_get_returns_registered_value() -> None:
    """``get`` возвращает ровно тот инстанс, что положили под ключом-классом."""
    registry = ComponentRegistry()
    value = _ComponentA()
    registry.set(key=_ComponentA, value=value)

    assert registry.get(_ComponentA) is value


def test_get_unregistered_key_raises_naming_registry_and_key() -> None:
    """``get`` незарегистрированного ключа бросает ``ComponentNotRegisteredError`` с именем реестра и ключа."""
    registry = ComponentRegistry()

    with pytest.raises(ComponentNotRegisteredError, match=r"registry='ComponentRegistry'.*_ComponentA"):
        registry.get(_ComponentA)


def test_set_overwrites_existing_value() -> None:
    """Повторный ``set`` под тем же ключом перезаписывает значение."""
    registry = ComponentRegistry()
    first = _ComponentA()
    second = _ComponentA()
    registry.set(key=_ComponentA, value=first)
    registry.set(key=_ComponentA, value=second)

    assert registry.get(_ComponentA) is second


def test_contains_reflects_registration() -> None:
    """``in`` отражает наличие ключа в registry."""

    class _ComponentB:
        """Второй ключ-тип компонента: в registry не кладётся."""

    registry = ComponentRegistry()
    registry.set(key=_ComponentA, value=_ComponentA())

    assert _ComponentA in registry
    assert _ComponentB not in registry
