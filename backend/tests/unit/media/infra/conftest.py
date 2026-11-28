"""
Фикстуры unit-тестов хранилища media: настоящий клиент aiobotocore без сети.

Клиент открывается тем же ``open_s3_client``, что и в приложении, поэтому тесты видят рабочую
конфигурацию. Ответы S3 подменяет ``AioStubber`` — он же сверяет параметры вызовов и форму ответов
с моделью API S3.
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from aiobotocore.stub import AioStubber
from botocore.exceptions import EndpointConnectionError
from pydantic import SecretStr

from app.media.infra.s3_client import open_s3_client
from app.media.infra.s3_object_storage import S3ObjectStorage
from app.shared.settings import MediaStorageSettings

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


@pytest.fixture(autouse=True)
def _isolated_aws_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Отрезает ``~/.aws`` и переменные ``AWS_*`` машины: botocore читает их поверх явной конфигурации."""
    for name in [name for name in os.environ if name.startswith("AWS_")]:
        monkeypatch.delenv(name)

    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "missing-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "missing-credentials"))


@pytest.fixture
def media_storage_settings() -> MediaStorageSettings:
    return MediaStorageSettings(
        MEDIA_S3_ENDPOINT_URL="http://s3.localhost:9050",
        MEDIA_S3_ACCESS_KEY_ID=SecretStr("test-access-key"),
        MEDIA_S3_SECRET_ACCESS_KEY=SecretStr("test-secret-key"),
    )


@pytest.fixture
async def s3_client(media_storage_settings: MediaStorageSettings) -> AsyncIterator[S3Client]:
    async with open_s3_client(media_storage_settings) as client:
        yield client


@pytest.fixture
def s3_stubber(s3_client: S3Client) -> Iterator[AioStubber]:
    """Подменяет ответы S3; ответ, положенный в очередь и не запрошенный, валит тест."""
    with AioStubber(s3_client) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def storage(s3_client: S3Client) -> S3ObjectStorage:
    return S3ObjectStorage(client=s3_client, bucket="media-private")


def _refuse_connection(**_: object) -> None:
    raise EndpointConnectionError(endpoint_url="http://s3.localhost:9050")


@pytest.fixture
async def unreachable_storage(media_storage_settings: MediaStorageSettings) -> AsyncIterator[S3ObjectStorage]:
    """Хранилище, до которого не достучаться: каждый запрос падает на подключении, без повторов."""
    settings = media_storage_settings.model_copy(update={"MEDIA_S3_MAX_ATTEMPTS": 1})
    async with open_s3_client(settings) as client:
        client.meta.events.register("before-send.s3", _refuse_connection)
        yield S3ObjectStorage(client=client, bucket="media-private")
