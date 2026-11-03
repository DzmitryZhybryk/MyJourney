import datetime as dt
from uuid import uuid4

import pytest

from app.users.application.schemas.commands import CreateUserCommand
from app.users.application.schemas.results import CurrentUserResult
from app.users.application.services.user import UserService
from app.users.exceptions import UserDeletedError, UserNotFoundError
from tests.builders import make_user_entity
from tests.fakes import FakeUserRepository, FakeUserUnitOfWork


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

    await user_service.create_user(command=command)

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

    await user_service.create_user(command=command)

    fake_user_uow.commit_mock.assert_not_awaited()


async def test_get_current_user_returns_profile(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """`get_current_user` отдаёт display_name найденного пользователя."""
    user_entity = make_user_entity(display_name="Alice D.")
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    result = await user_service.get_current_user(user_id=user_entity.user_id)

    assert result == CurrentUserResult(display_name="Alice D.")


async def test_get_current_user_does_not_commit(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """`get_current_user` — read-only use case: транзакция закрывается без commit."""
    user_entity = make_user_entity()
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    await user_service.get_current_user(user_id=user_entity.user_id)

    fake_user_uow.commit_mock.assert_not_awaited()


async def test_get_current_user_unknown_id_raises_not_found(user_service: UserService) -> None:
    """`get_current_user` по неизвестному id бросает UserNotFoundError."""
    with pytest.raises(UserNotFoundError):
        await user_service.get_current_user(user_id=uuid4())


async def test_get_current_user_soft_deleted_raises_gone(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
) -> None:
    """`get_current_user` для soft-deleted пользователя бросает UserDeletedError."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    with pytest.raises(UserDeletedError):
        await user_service.get_current_user(user_id=user_entity.user_id)
