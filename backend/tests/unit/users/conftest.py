"""
Фикстуры домена users: ``UserService``, собранный на фейках.

Фейки I/O-границы (``fake_user_repository``/``fake_user_uow``) живут в корневом
``tests/conftest.py`` — их переиспользует и api-уровень (``tests/api/users``).
"""

import pytest

from app.users.application.services.user import UserService
from tests.fakes import FakeUserUnitOfWork


@pytest.fixture
def user_service(fake_user_uow: FakeUserUnitOfWork) -> UserService:
    return UserService(uow=fake_user_uow)
