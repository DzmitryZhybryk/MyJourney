import datetime as dt
from uuid import UUID

from app.shared.events.event import IntegrationEvent


class AccountChangedEvent(IntegrationEvent):
    """
    Учётная запись изменилась: её публичное состояние на момент коммита.

    Подписчик хранит последний снимок и по ``version`` отбрасывает тот, что старше уже применённого:
    снимки могут прийти не по порядку и повторно.
    """

    user_id: UUID
    email: str
    username: str
    role: str
    plan: str
    email_verified_at: dt.datetime | None
    registered_at: dt.datetime
    deleted_at: dt.datetime | None
    version: int
