"""
Integration-харнес хранилища media: S3-эмулятор RustFS в testcontainers.

Контейнер поднимается синхронно на всю сессию. Бакеты настраивает тот же ``bootstrap_buckets``, что
и dev-стек, — асинхронная session-фикстура в session-loop'е, отдающая наружу только настройки: ни один
объект, привязанный к event loop, не переходит в loop'ы тестов. Хранилища каждый тест берёт из
``MediaStorageComponent``, поэтому проверяется и то, что порт смотрит в свой бакет. Тесты изолированы
префиксом ключа, а не пересозданием бакетов.
"""

from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

from app.media.application.ports.private_storage import PrivateStoragePort
from app.media.application.ports.public_storage import PublicStoragePort
from app.media.infra.component import MediaStorageComponent
from app.media.infra.s3_client import open_s3_client
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.settings import MediaStorageSettings
from devtools.storage_bootstrap import bootstrap_buckets

_RUSTFS_IMAGE = "rustfs/rustfs:1.0.4@sha256:ed9210d6411d77ffceb70d94b964a3cb7d225983368bc25bebe01e995293dcc2"
_RUSTFS_PORT = 9000
_ACCESS_KEY_ID = "integration-access-key"
_SECRET_ACCESS_KEY = "integration-secret-key"
_FRONTEND_ORIGIN = "http://frontend.test"


@pytest.fixture(scope="session")
def _rustfs_container() -> Iterator[DockerContainer]:
    container = (
        DockerContainer(image=_RUSTFS_IMAGE)
        .with_env(key="RUSTFS_ACCESS_KEY", value=_ACCESS_KEY_ID)
        .with_env(key="RUSTFS_SECRET_KEY", value=_SECRET_ACCESS_KEY)
        .with_exposed_ports(_RUSTFS_PORT)
        .waiting_for(HttpWaitStrategy(port=_RUSTFS_PORT, path="/health").for_status_code(200))
    )
    with container:
        yield container


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def media_storage_settings(_rustfs_container: DockerContainer) -> MediaStorageSettings:
    """Настройки хранилища на контейнер, бакеты которого уже настроены bootstrap'ом."""
    host = _rustfs_container.get_container_host_ip()
    port = _rustfs_container.get_exposed_port(_RUSTFS_PORT)
    settings = MediaStorageSettings(
        MEDIA_S3_ENDPOINT_URL=f"http://{host}:{port}",
        MEDIA_S3_ACCESS_KEY_ID=SecretStr(_ACCESS_KEY_ID),
        MEDIA_S3_SECRET_ACCESS_KEY=SecretStr(_SECRET_ACCESS_KEY),
    )
    async with open_s3_client(settings) as client:
        await bootstrap_buckets(
            client=client,
            private_bucket=settings.MEDIA_S3_PRIVATE_BUCKET,
            public_bucket=settings.MEDIA_S3_PUBLIC_BUCKET,
            cors_allowed_origins=(_FRONTEND_ORIGIN,),
        )

    return settings


@pytest.fixture
def frontend_origin() -> str:
    """Origin фронта, которому bootstrap разрешил PUT в приватный бакет."""
    return _FRONTEND_ORIGIN


@pytest.fixture
async def media_storage_registry(media_storage_settings: MediaStorageSettings) -> AsyncIterator[ComponentRegistry]:
    component = MediaStorageComponent(settings=media_storage_settings)
    registry = ComponentRegistry()
    await component.startup(registry)
    yield registry
    await component.shutdown()


@pytest.fixture
def private_storage(media_storage_registry: ComponentRegistry) -> PrivateStoragePort:
    return media_storage_registry.get(PrivateStoragePort)


@pytest.fixture
def public_storage(media_storage_registry: ComponentRegistry) -> PublicStoragePort:
    return media_storage_registry.get(PublicStoragePort)


@pytest.fixture
def key_prefix() -> str:
    """Свой префикс ключей на тест: бакеты общие на сессию, объекты тестов не пересекаются."""
    return f"{uuid4()}/"


@pytest.fixture
async def anonymous_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP-клиент без ключей хранилища: так ходит браузер."""
    async with httpx.AsyncClient() as client:
        yield client
