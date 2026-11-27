import datetime as dt
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events import AccountChangedEvent, ProfileChangedEvent
from app.shared.events.publisher import TaskBusEventPublisher
from tests.fakes import FakeTaskBus
from tests.fakes.procrastinate import DeferredTask


async def test_publish_defers_one_task_per_subscriber_with_json_event(fake_task_bus: FakeTaskBus) -> None:
    """Событие ставит по задаче на каждого подписчика в сессии use case'а, с событием JSON-словарём."""
    session = cast(AsyncSession, object())
    publisher = TaskBusEventPublisher(
        task_bus=fake_task_bus,
        subscriptions={ProfileChangedEvent: ("first_subscriber", "second_subscriber")},
    )
    event = ProfileChangedEvent(
        user_id=uuid4(),
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        version=2,
    )

    await publisher.bind_to(session).publish(event)

    payload = {
        "user_id": str(event.user_id),
        "display_name": "alice",
        "marketing_emails_consent": True,
        "terms_accepted_at": "2026-01-01T00:00:00Z",
        "version": 2,
    }
    assert fake_task_bus.bound_session is session
    assert fake_task_bus.bound.deferred == [
        DeferredTask(task_name="first_subscriber", lock=None, kwargs={"event": payload}),
        DeferredTask(task_name="second_subscriber", lock=None, kwargs={"event": payload}),
    ]


async def test_publish_without_subscribers_defers_nothing(fake_task_bus: FakeTaskBus) -> None:
    """Событие без подписчиков задач не ставит."""
    publisher = TaskBusEventPublisher(
        task_bus=fake_task_bus,
        subscriptions={ProfileChangedEvent: ("profile_subscriber",)},
    )
    event = AccountChangedEvent(
        user_id=uuid4(),
        email="user@example.com",
        username="user",
        role="user",
        plan="free",
        email_verified_at=None,
        registered_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        deleted_at=None,
        version=1,
    )

    await publisher.bind_to(cast(AsyncSession, object())).publish(event)

    assert fake_task_bus.bound.deferred == []
