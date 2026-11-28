import datetime as dt
from uuid import uuid4

import pytest

from app.shared.events import ProfileChangedEvent
from app.users.application.schemas.commands import CreateUserCommand, UpdateCurrentUserCommand
from app.users.application.schemas.results import CurrentUserResult
from app.users.application.services.user import UserService
from app.users.exceptions import UserDeletedError, UserNotFoundError
from tests.builders import make_user_entity
from tests.fakes import FakeEventPublisher, FakeUserRepository, FakeUserUnitOfWork


async def test_create_user_inserts_mapped_entity(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """`create_user` кладёт в репозиторий entity с полями из команды."""
    command = CreateUserCommand(
        user_id=uuid4(),
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )

    await user_service.create_user(command)

    stored = fake_user_repository.by_user_id[command.user_id]
    assert stored.display_name == command.display_name
    assert stored.marketing_emails_consent == command.marketing_emails_consent
    assert stored.terms_accepted_at == command.terms_accepted_at


async def test_create_user_does_not_commit(
    user_service: UserService,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """`create_user` НЕ коммитит — фиксацией владеет вызывающий use-case (Option A)."""
    command = CreateUserCommand(
        user_id=uuid4(),
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )

    await user_service.create_user(command)

    fake_user_uow.commit_mock.assert_not_awaited()


async def test_create_user_publishes_profile_changed_with_first_version(
    user_service: UserService,
    fake_user_uow: FakeUserUnitOfWork,
    fake_event_publisher: FakeEventPublisher,
) -> None:
    """`create_user` публикует в сессии UoW снимок нового профиля с версией 1."""
    command = CreateUserCommand(
        user_id=uuid4(),
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )

    await user_service.create_user(command)

    assert fake_event_publisher.bound_session is fake_user_uow.session
    assert fake_event_publisher.bound.published == [
        ProfileChangedEvent(
            user_id=command.user_id,
            display_name="alice",
            marketing_emails_consent=True,
            terms_accepted_at=command.terms_accepted_at,
            version=1,
        ),
    ]


async def test_get_current_user_returns_profile(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """`get_current_user` отдаёт имя и согласие на рассылку найденного пользователя."""
    user_entity = make_user_entity(display_name="Alice D.", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    result = await user_service.get_current_user(user_entity.user_id)

    assert result == CurrentUserResult(display_name="Alice D.", marketing_emails_consent=True)


async def test_get_current_user_does_not_commit(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """`get_current_user` — read-only use case: транзакция закрывается без commit."""
    user_entity = make_user_entity()
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    await user_service.get_current_user(user_entity.user_id)

    fake_user_uow.commit_mock.assert_not_awaited()


async def test_get_current_user_unknown_id_raises_not_found(user_service: UserService) -> None:
    """`get_current_user` по неизвестному id бросает UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await user_service.get_current_user(uuid4())


async def test_get_current_user_soft_deleted_raises_gone(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """`get_current_user` для soft-deleted пользователя бросает UserDeletedError."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    with pytest.raises(UserDeletedError):
        await user_service.get_current_user(user_entity.user_id)


async def test_update_current_user_writes_commits_and_returns_profile(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """`update_current_user` меняет переданные поля, записывает, коммитит и отдаёт новый профиль."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    result = await user_service.update_current_user(
        user_id=user_entity.user_id,
        command=UpdateCurrentUserCommand(display_name="Alice D.", marketing_emails_consent=False),
    )

    assert result == CurrentUserResult(display_name="Alice D.", marketing_emails_consent=False)
    assert fake_user_repository.updated_user_ids == [user_entity.user_id]
    fake_user_uow.commit_mock.assert_awaited_once()


async def test_update_current_user_publishes_profile_changed_with_next_version(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
    fake_event_publisher: FakeEventPublisher,
) -> None:
    """`update_current_user` публикует в сессии UoW снимок нового профиля с версией на единицу выше."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True, version=2)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    await user_service.update_current_user(
        user_id=user_entity.user_id,
        command=UpdateCurrentUserCommand(display_name="Alice D.", marketing_emails_consent=False),
    )

    assert fake_event_publisher.bound_session is fake_user_uow.session
    assert fake_event_publisher.bound.published == [
        ProfileChangedEvent(
            user_id=user_entity.user_id,
            display_name="Alice D.",
            marketing_emails_consent=False,
            terms_accepted_at=user_entity.terms_accepted_at,
            version=3,
        ),
    ]


async def test_update_current_user_keeps_fields_not_in_command(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """Поле, которого нет в команде (None), сохраняет прежнее значение."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    result = await user_service.update_current_user(
        user_id=user_entity.user_id,
        command=UpdateCurrentUserCommand(marketing_emails_consent=False),
    )

    assert result == CurrentUserResult(display_name="alice", marketing_emails_consent=False)


async def test_update_current_user_unknown_id_raises_not_found(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """Неизвестный id → UserNotFoundError; ничего не записано и не закоммичено."""
    with pytest.raises(UserNotFoundError):
        await user_service.update_current_user(
            user_id=uuid4(),
            command=UpdateCurrentUserCommand(display_name="Alice D."),
        )

    assert fake_user_repository.updated_user_ids == []
    fake_user_uow.commit_mock.assert_not_awaited()


async def test_update_current_user_soft_deleted_raises_gone_and_changes_nothing(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
    fake_event_publisher: FakeEventPublisher,
) -> None:
    """Soft-deleted → UserDeletedError; поля и updated_at прежние, записи, события и коммита нет."""
    updated_at = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
    user_entity = make_user_entity(
        display_name="alice",
        updated_at=updated_at,
        deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC),
    )
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    with pytest.raises(UserDeletedError):
        await user_service.update_current_user(
            user_id=user_entity.user_id,
            command=UpdateCurrentUserCommand(display_name="Alice D."),
        )

    assert user_entity.display_name == "alice"
    assert user_entity.updated_at == updated_at
    assert fake_user_repository.updated_user_ids == []
    assert fake_event_publisher.bound.published == []
    fake_user_uow.commit_mock.assert_not_awaited()
