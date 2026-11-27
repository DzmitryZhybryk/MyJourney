import datetime as dt
from uuid import UUID

from app.shared.events.event import IntegrationEvent


class ProfileChangedEvent(IntegrationEvent):
    """
    Профиль пользователя изменился: его публичное состояние на момент коммита.

    Подписчик хранит последний снимок и по ``version`` отбрасывает тот, что старше уже применённого:
    снимки могут прийти не по порядку и повторно.
    """

    user_id: UUID
    display_name: str
    marketing_emails_consent: bool
    terms_accepted_at: dt.datetime
    version: int
