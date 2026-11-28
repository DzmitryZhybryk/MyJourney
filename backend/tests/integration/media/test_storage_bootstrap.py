import httpx
import pytest

from app.media.infra.s3_client import open_s3_client
from app.shared.settings import MediaStorageSettings
from devtools.storage_bootstrap import bootstrap_buckets


async def test_bootstrap_buckets_second_run_keeps_buckets_working(
    media_storage_settings: MediaStorageSettings, frontend_origin: str
) -> None:
    """Повторный запуск поверх настроенных бакетов не падает и не ломает их настройки."""
    async with open_s3_client(media_storage_settings) as client:
        await bootstrap_buckets(
            client=client,
            private_bucket=media_storage_settings.MEDIA_S3_PRIVATE_BUCKET,
            public_bucket=media_storage_settings.MEDIA_S3_PUBLIC_BUCKET,
            cors_allowed_origins=(frontend_origin,),
        )
        buckets = await client.list_buckets()

    assert {bucket.get("Name") for bucket in buckets.get("Buckets", ())} >= {
        media_storage_settings.MEDIA_S3_PRIVATE_BUCKET,
        media_storage_settings.MEDIA_S3_PUBLIC_BUCKET,
    }


@pytest.mark.parametrize(
    ("origin_is_frontend", "expected_status"),
    [pytest.param(True, 200, id="frontend_origin"), pytest.param(False, 403, id="foreign_origin")],
)
async def test_private_bucket_cors_allows_put_only_from_frontend(
    media_storage_settings: MediaStorageSettings,
    anonymous_http_client: httpx.AsyncClient,
    frontend_origin: str,
    origin_is_frontend: bool,
    expected_status: int,
) -> None:
    """Preflight PUT в приватный бакет проходит с origin фронта и отвергается с чужого."""
    origin = frontend_origin if origin_is_frontend else "http://evil.example"

    response = await anonymous_http_client.options(
        f"{media_storage_settings.MEDIA_S3_ENDPOINT_URL}/{media_storage_settings.MEDIA_S3_PRIVATE_BUCKET}/key",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type,if-none-match",
        },
    )

    assert response.status_code == expected_status


async def test_public_bucket_is_not_listed_anonymously(
    media_storage_settings: MediaStorageSettings, anonymous_http_client: httpx.AsyncClient
) -> None:
    """Публичный бакет отдаёт объекты по ключу, но не их перечень: ключи остаются неугадываемыми."""
    response = await anonymous_http_client.get(
        f"{media_storage_settings.MEDIA_S3_ENDPOINT_URL}/{media_storage_settings.MEDIA_S3_PUBLIC_BUCKET}",
        params={"list-type": "2"},
    )

    assert response.status_code == 403
