"""
Протоколы публикации межмодульных событий для application-слоя.

Издатель знает только событие; кому его доставить, решает composition root. Событие публикуется
в транзакции use case'а: его видят подписчики, только если записи use case'а закоммичены.
"""

from typing import TYPE_CHECKING, Protocol

from app.shared.events.event import IntegrationEvent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SessionBoundEventPublisherPort(Protocol):
    """Контракт публикации события в текущей SA-транзакции."""

    async def publish(self, event: IntegrationEvent) -> None:
        """
        Публикует событие в той же транзакции, что и записи use case'а; фиксирует его commit UnitOfWork.

        Scenarios:
            - use case, который меняет состояние, интересное другим модулям

        Args:
            event: Событие с состоянием после изменений use case'а
        """
        ...


class EventPublisherPort(Protocol):
    """Контракт издателя событий: публикация возможна только в транзакции use case'а."""

    def bind_to(self, session: AsyncSession) -> SessionBoundEventPublisherPort:
        """
        Привязывает публикацию событий к транзакции сессии.

        Scenarios:
            - use case, который меняет состояние, интересное другим модулям

        Args:
            session: Активная сессия UnitOfWork

        Returns:
            Издатель, чей ``publish`` попадает в транзакцию сессии
        """
        ...
