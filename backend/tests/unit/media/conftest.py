"""
Фикстуры домена media (unit): сборка ``MediaConfigService`` на фейке UoW.

Фейки I/O-границы (``fake_media_config_repository``, ``fake_media_uow``) живут в корневом
``tests/conftest.py`` — их переиспользует и api-уровень.
"""

import pytest

from app.media.application.services.media_config import MediaConfigService
from tests.fakes import FakeMediaUnitOfWork


@pytest.fixture
def media_config_service(fake_media_uow: FakeMediaUnitOfWork) -> MediaConfigService:
    return MediaConfigService(fake_media_uow)
