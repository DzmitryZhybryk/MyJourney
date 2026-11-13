import datetime as dt

import httpx
import pytest

from app.media.application.ports.private_storage import ObjectInfo, PrivateStoragePort
from app.media.application.ports.public_storage import PublicStoragePort
from app.media.exceptions import ObjectNotFoundError, ObjectTooLargeError
from app.shared.settings import MediaStorageSettings


async def test_signed_upload_accepts_declared_object_once(
    private_storage: PrivateStoragePort, anonymous_http_client: httpx.AsyncClient, key_prefix: str
) -> None:
    """По ссылке браузер кладёт ровно заявленный объект, повтор по той же ссылке получает 412."""
    key = f"{key_prefix}original.jpg"
    signed_upload = await private_storage.sign_upload(
        key=key, content_type="image/jpeg", size_bytes=100, expires_in=dt.timedelta(minutes=5)
    )
    headers = dict(signed_upload.required_headers)

    first = await anonymous_http_client.put(signed_upload.url, content=b"x" * 100, headers=headers)
    repeat = await anonymous_http_client.put(signed_upload.url, content=b"y" * 100, headers=headers)

    assert (first.status_code, repeat.status_code) == (200, 412)
    assert await private_storage.head_object(key) == ObjectInfo(size_bytes=100, content_type="image/jpeg")
    assert await private_storage.get_object(key=key, max_bytes=100) == b"x" * 100


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        pytest.param(b"x" * 101, "image/jpeg", id="bigger_than_signed"),
        pytest.param(b"x" * 100, "image/png", id="other_content_type"),
    ],
)
async def test_signed_upload_rejects_undeclared_object(
    private_storage: PrivateStoragePort,
    anonymous_http_client: httpx.AsyncClient,
    key_prefix: str,
    body: bytes,
    content_type: str,
) -> None:
    """Тело не того размера или типа хранилище отвергает, и объект не появляется."""
    key = f"{key_prefix}original.jpg"
    signed_upload = await private_storage.sign_upload(
        key=key, content_type="image/jpeg", size_bytes=100, expires_in=dt.timedelta(minutes=5)
    )

    response = await anonymous_http_client.put(
        signed_upload.url, content=body, headers={**dict(signed_upload.required_headers), "Content-Type": content_type}
    )

    assert response.status_code == 403
    assert await private_storage.head_object(key) is None


async def test_get_object_over_limit_raises_too_large(
    private_storage: PrivateStoragePort, anonymous_http_client: httpx.AsyncClient, key_prefix: str
) -> None:
    """Записанный объект больше лимита чтения отвергается."""
    key = f"{key_prefix}original.jpg"
    signed_upload = await private_storage.sign_upload(
        key=key, content_type="image/jpeg", size_bytes=100, expires_in=dt.timedelta(minutes=5)
    )
    await anonymous_http_client.put(signed_upload.url, content=b"x" * 100, headers=dict(signed_upload.required_headers))

    with pytest.raises(ObjectTooLargeError):
        await private_storage.get_object(key=key, max_bytes=99)


async def test_get_object_missing_object_raises_not_found(private_storage: PrivateStoragePort, key_prefix: str) -> None:
    """Отсутствующий объект — `ObjectNotFoundError`."""
    with pytest.raises(ObjectNotFoundError):
        await private_storage.get_object(key=f"{key_prefix}original.jpg", max_bytes=100)


async def test_public_object_is_read_anonymously_with_cache_control(
    public_storage: PublicStoragePort,
    anonymous_http_client: httpx.AsyncClient,
    media_storage_settings: MediaStorageSettings,
    key_prefix: str,
) -> None:
    """Записанное в публичный бакет читается без ключей, с типом и `Cache-Control` объекта."""
    key = f"{key_prefix}r1/thumb.webp"
    await public_storage.put_object(
        key=key, body=b"webp", content_type="image/webp", cache_control="public, max-age=31536000, immutable"
    )

    response = await anonymous_http_client.get(
        f"{media_storage_settings.MEDIA_S3_ENDPOINT_URL}/{media_storage_settings.MEDIA_S3_PUBLIC_BUCKET}/{key}"
    )

    assert response.status_code == 200
    assert response.content == b"webp"
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


async def test_private_object_is_not_read_anonymously(
    private_storage: PrivateStoragePort,
    anonymous_http_client: httpx.AsyncClient,
    media_storage_settings: MediaStorageSettings,
    key_prefix: str,
) -> None:
    """Объект приватного бакета без ключей не читается."""
    key = f"{key_prefix}original.jpg"
    signed_upload = await private_storage.sign_upload(
        key=key, content_type="image/jpeg", size_bytes=3, expires_in=dt.timedelta(minutes=5)
    )
    await anonymous_http_client.put(signed_upload.url, content=b"abc", headers=dict(signed_upload.required_headers))

    response = await anonymous_http_client.get(
        f"{media_storage_settings.MEDIA_S3_ENDPOINT_URL}/{media_storage_settings.MEDIA_S3_PRIVATE_BUCKET}/{key}"
    )

    assert response.status_code == 403


async def test_delete_objects_removes_existing_and_ignores_missing_keys(
    public_storage: PublicStoragePort,
    anonymous_http_client: httpx.AsyncClient,
    media_storage_settings: MediaStorageSettings,
    key_prefix: str,
) -> None:
    """Удаление убирает существующие объекты и не спотыкается об отсутствующий ключ."""
    key = f"{key_prefix}r1/thumb.webp"
    await public_storage.put_object(key=key, body=b"webp", content_type="image/webp", cache_control="no-cache")

    await public_storage.delete_objects([key, f"{key_prefix}missing.webp"])

    response = await anonymous_http_client.get(
        f"{media_storage_settings.MEDIA_S3_ENDPOINT_URL}/{media_storage_settings.MEDIA_S3_PUBLIC_BUCKET}/{key}"
    )
    assert response.status_code == 404
