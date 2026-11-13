from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from aiobotocore.config import AioConfig
from aiobotocore.session import get_session

from app.shared.settings import MediaStorageSettings

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client


def open_s3_client(settings: MediaStorageSettings) -> AbstractAsyncContextManager[S3Client]:
    """
    Открывает клиент S3-совместимого хранилища по настройкам media.

    Scenarios:
        - старт API-процесса и воркера: клиент на время жизни процесса
        - настройка бакетов локального эмулятора

    Args:
        settings: Адрес, ключи, регион, ретраи и таймауты хранилища

    Returns:
        Контекст, который открывает клиент на входе и закрывает на выходе
    """
    return get_session().create_client(
        service_name="s3",
        region_name=settings.MEDIA_S3_REGION,
        endpoint_url=settings.MEDIA_S3_ENDPOINT_URL,
        aws_access_key_id=settings.MEDIA_S3_ACCESS_KEY_ID.get_secret_value(),
        aws_secret_access_key=settings.MEDIA_S3_SECRET_ACCESS_KEY.get_secret_value(),
        config=AioConfig(
            # Без явного SigV4 botocore подписывает presigned-ссылки части регионов по SigV2,
            # и Content-Length с If-None-Match в подпись не попадают.
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            # Контрольные суммы по умолчанию (CRC32 на каждый запрос) R2 принимает не везде.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            retries={"mode": "standard", "total_max_attempts": settings.MEDIA_S3_MAX_ATTEMPTS},
            connect_timeout=settings.MEDIA_S3_CONNECT_TIMEOUT_SECONDS,
            read_timeout=settings.MEDIA_S3_READ_TIMEOUT_SECONDS,
        ),
    )
