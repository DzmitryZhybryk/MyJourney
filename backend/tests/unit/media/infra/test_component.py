from app.media.application.ports.private_storage import PrivateStoragePort
from app.media.application.ports.public_storage import PublicStoragePort
from app.media.infra.component import MediaStorageComponent
from app.media.infra.s3_object_storage import S3ObjectStorage
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.settings import MediaStorageSettings


async def test_media_storage_component_publishes_storage_of_each_bucket(
    media_storage_settings: MediaStorageSettings,
) -> None:
    """Старт кладёт в реестр хранилище приватного и хранилище публичного бакета — два разных объекта."""
    component = MediaStorageComponent(settings=media_storage_settings)
    registry = ComponentRegistry()

    await component.startup(registry)
    try:
        private_storage = registry.get(PrivateStoragePort)
        public_storage = registry.get(PublicStoragePort)
        assert isinstance(private_storage, S3ObjectStorage)
        assert isinstance(public_storage, S3ObjectStorage)
        assert private_storage is not public_storage
    finally:
        await component.shutdown()
