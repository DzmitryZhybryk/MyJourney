from typing import Final

from app.backoffice.infra.tasks import apply_account_changed, apply_profile_changed
from app.shared.events import AccountChangedEvent, ProfileChangedEvent
from app.shared.events.publisher import EventSubscriptions

# Подписки всех модулей на события: какие задачи издатель ставит на каждое событие.
EVENT_SUBSCRIPTIONS: Final[EventSubscriptions] = {
    AccountChangedEvent: (apply_account_changed.name,),
    ProfileChangedEvent: (apply_profile_changed.name,),
}
