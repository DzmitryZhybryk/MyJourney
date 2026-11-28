import pytest

from app.backoffice.application.services.account import AccountService
from tests.fakes import FakeBackofficeUnitOfWork


@pytest.fixture
def account_service(fake_backoffice_uow: FakeBackofficeUnitOfWork) -> AccountService:
    return AccountService(fake_backoffice_uow)
