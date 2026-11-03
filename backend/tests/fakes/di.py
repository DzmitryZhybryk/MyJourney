"""Фейк ``BaseComponent``: пишет старт и остановку в общий журнал, может упасть на любой из них."""

from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry


class FakeComponent(BaseComponent):
    """
    Компонент, который ничем не владеет и только отмечается в журнале.

    Несколько фейков делят один ``events`` — по нему тест видит порядок старта и остановки
    между компонентами. ``startup_error``/``shutdown_error`` — исключение, которым упасть
    вместо записи; ``registry`` — реестр, полученный на старте.
    """

    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        startup_error: Exception | None = None,
        shutdown_error: Exception | None = None,
    ) -> None:
        self._name = name
        self._events = events
        self._startup_error = startup_error
        self._shutdown_error = shutdown_error
        self.registry: ComponentRegistry | None = None

    async def startup(self, registry: ComponentRegistry) -> None:
        if self._startup_error is not None:
            raise self._startup_error

        self.registry = registry
        self._events.append(f"start:{self._name}")

    async def shutdown(self) -> None:
        if self._shutdown_error is not None:
            raise self._shutdown_error

        self._events.append(f"stop:{self._name}")
