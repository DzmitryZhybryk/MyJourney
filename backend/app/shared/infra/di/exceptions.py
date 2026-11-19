"""Исключения для компонентов инфраструктуры."""

from app.shared.exceptions.base import InvariantViolationError


class ComponentNotRegisteredError(InvariantViolationError):
    """Компонента нет в реестре: композиционный корень не зарегистрировал его до обращения."""

    message = "Компонент не зарегистрирован в реестре"
