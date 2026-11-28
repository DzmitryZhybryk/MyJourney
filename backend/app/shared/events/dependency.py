"""FastAPI-зависимость издателя событий."""

from fastapi import Request

from app.shared.events.ports import EventPublisherPort
from app.shared.events.publisher import TaskBusEventPublisher
from app.shared.schemas.base import BFastAPI

__all__ = [
    "event_publisher_dependency",
]


def event_publisher_dependency(request: Request) -> EventPublisherPort:
    """
    Возвращает издателя событий из реестра приложения.

    Scenarios:
        - запрос, use case которого меняет состояние, интересное другим модулям
    """
    app: BFastAPI = request.app
    return app.registry.get(TaskBusEventPublisher)
