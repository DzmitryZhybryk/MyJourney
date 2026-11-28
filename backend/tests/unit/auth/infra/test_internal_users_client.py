"""Перепутанное или потерянное поле между ``CreateUserRequest`` и командой users ловит только этот тест."""

import datetime as dt
from uuid import uuid4

from app.auth.application.ports.users_client import CreateUserRequest
from app.auth.infra.clients.internal_users_client import InternalUsersClient
from app.users.application.services.user import UserService
from tests.fakes import FakeUserRepository, FakeUserUnitOfWork


async def test_create_user_maps_fields_and_persists_via_user_service(
    user_service: UserService,
    fake_user_repository: FakeUserRepository,
    fake_user_uow: FakeUserUnitOfWork,
) -> None:
    """Поля запроса доходят до пользователя в users; коммит остаётся за вызывающим."""
    user_id = uuid4()
    terms_accepted_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

    await InternalUsersClient(user_service).create_user(
        CreateUserRequest(
            user_id=user_id,
            display_name="newuser",
            marketing_emails_consent=True,
            terms_accepted_at=terms_accepted_at,
        ),
    )

    user_entity = fake_user_repository.by_user_id[user_id]
    assert user_entity.display_name == "newuser"
    assert user_entity.marketing_emails_consent is True
    assert user_entity.terms_accepted_at == terms_accepted_at
    fake_user_uow.commit_mock.assert_not_awaited()
