from contextlib import AsyncExitStack

from app.media.application.ports.private_storage import PrivateStoragePort
from app.media.application.ports.public_storage import PublicStoragePort
from app.media.infra.s3_client import open_s3_client
from app.media.infra.s3_object_storage import S3ObjectStorage
from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.settings import MediaStorageSettings


class MediaStorageComponent(BaseComponent):
    """Клиент S3 на время жизни процесса и хранилища обоих бакетов media в реестре."""

    def __init__(self, settings: MediaStorageSettings) -> None:
        self._settings = settings
        self._exit_stack = AsyncExitStack()

    async def startup(self, registry: ComponentRegistry) -> None:
        client = await self._exit_stack.enter_async_context(open_s3_client(self._settings))
        registry.set(
            key=PrivateStoragePort,
            value=S3ObjectStorage(client=client, bucket=self._settings.MEDIA_S3_PRIVATE_BUCKET),
        )
        registry.set(
            key=PublicStoragePort,
            value=S3ObjectStorage(client=client, bucket=self._settings.MEDIA_S3_PUBLIC_BUCKET),
        )

    async def shutdown(self) -> None:
        await self._exit_stack.aclose()
