import datetime as dt
from urllib.parse import parse_qs, urlsplit

import pytest

from app.media.infra.s3_client import open_s3_client
from app.media.infra.s3_object_storage import S3ObjectStorage
from app.shared.settings import MediaStorageSettings


async def test_open_s3_client_takes_connection_and_network_policy_from_settings(
    media_storage_settings: MediaStorageSettings,
) -> None:
    """Адрес, регион, число попыток и таймауты клиента берутся из настроек; попытки — всего, не повторы."""
    settings = media_storage_settings.model_copy(
        update={
            "MEDIA_S3_REGION": "eu-central-1",
            "MEDIA_S3_MAX_ATTEMPTS": 5,
            "MEDIA_S3_CONNECT_TIMEOUT_SECONDS": 2.0,
            "MEDIA_S3_READ_TIMEOUT_SECONDS": 7.0,
        },
    )

    async with open_s3_client(settings) as client:
        config = client.meta.config
        assert (client.meta.endpoint_url, client.meta.region_name) == ("http://s3.localhost:9050", "eu-central-1")
        assert config.retries == {"mode": "standard", "total_max_attempts": 5}
        assert (config.connect_timeout, config.read_timeout) == (2.0, 7.0)


async def test_open_s3_client_sends_checksums_only_when_required(media_storage_settings: MediaStorageSettings) -> None:
    """Контрольные суммы считаются только там, где их требует API, — иначе R2 отвергает запросы."""
    async with open_s3_client(media_storage_settings) as client:
        config = client.meta.config
        assert (config.request_checksum_calculation, config.response_checksum_validation) == (
            "when_required",
            "when_required",
        )


@pytest.mark.parametrize("region", ["us-east-1", "auto", "eu-central-1"])
async def test_open_s3_client_presigns_with_sigv4_in_any_region(
    media_storage_settings: MediaStorageSettings, region: str
) -> None:
    """В любом регионе ссылка на загрузку подписана SigV4 — по SigV2 размер и запрет перезаписи не подписываются."""
    settings = media_storage_settings.model_copy(update={"MEDIA_S3_REGION": region})

    async with open_s3_client(settings) as client:
        signed_upload = await S3ObjectStorage(client=client, bucket="media-private").sign_upload(
            key="u1/f1/original.jpg", content_type="image/jpeg", size_bytes=100, expires_in=dt.timedelta(minutes=1)
        )

    query = parse_qs(urlsplit(signed_upload.url).query)
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert "AWSAccessKeyId" not in query
