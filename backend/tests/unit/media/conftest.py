import pytest

from app.media.application.services.media_config import MediaConfigService
from tests.fakes import FakeMediaUnitOfWork


@pytest.fixture
def media_config_service(fake_media_uow: FakeMediaUnitOfWork) -> MediaConfigService:
    return MediaConfigService(fake_media_uow)
