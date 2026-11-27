"""Фейки ``EventPublisherPort`` / ``SessionBoundEventPublisherPort`` с записью событий для state-ассертов."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events import EventPublisherPort, IntegrationEvent, SessionBoundEventPublisherPort


class FakeSessionBoundEventPublisher(SessionBoundEventPublisherPort):
    """Сессионно-привязанный фейк: пишет события в ``published`` вместо постановки задач подписчиков."""

    def __init__(self) -> None:
        self.published: list[IntegrationEvent] = []

    async def publish(self, event: IntegrationEvent) -> None:
        self.published.append(event)


class FakeEventPublisher(EventPublisherPort):
    """
    Фейк ``EventPublisherPort``: ``bind_to`` запоминает переданную сессию и отдаёт один общий
    ``FakeSessionBoundEventPublisher`` — тест проверяет и событие, и что оно опубликовано в сессии UoW.
    """

    def __init__(self) -> None:
        self.bound = FakeSessionBoundEventPublisher()
        self.bound_session: AsyncSession | None = None

    def bind_to(self, session: AsyncSession) -> SessionBoundEventPublisherPort:
        self.bound_session = session
        return self.bound
