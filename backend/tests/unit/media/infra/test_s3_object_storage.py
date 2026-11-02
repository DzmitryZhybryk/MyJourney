import datetime as dt
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, urlsplit

import pytest
from aiobotocore.response import StreamingBody
from aiobotocore.stub import AioStubber
from aiohttp import ClientPayloadError

from app.media.application.ports.private_storage import ObjectInfo
from app.media.exceptions import (
    ObjectNotFoundError,
    ObjectStoragePersistentError,
    ObjectStorageTemporaryError,
    ObjectTooLargeError,
)
from app.media.infra.s3_object_storage import S3ObjectStorage
from tests.fakes import FakeS3ResponseStream

_STORAGE_CALLS: list[tuple[str, Callable[[S3ObjectStorage], Awaitable[object]]]] = [
    ("head_object", lambda storage: storage.head_object("u1/f1/original.jpg")),
    ("get_object", lambda storage: storage.get_object(key="u1/f1/original.jpg", max_bytes=100)),
    (
        "put_object",
        lambda storage: storage.put_object(
            key="u1/f1/r1/thumb.webp", body=b"webp", content_type="image/webp", cache_control="no-cache"
        ),
    ),
    ("delete_objects", lambda storage: storage.delete_objects(["u1/f1/original.jpg"])),
]


async def test_sign_upload_signs_type_size_and_overwrite_ban(storage: S3ObjectStorage) -> None:
    """Ссылка подписана SigV4 на хост хранилища, в подпись входят тип, размер и запрет перезаписи."""
    expires_in = dt.timedelta(minutes=15)
    signed_from = dt.datetime.now(dt.UTC)

    signed_upload = await storage.sign_upload(
        key="u1/f1/original.jpg", content_type="image/jpeg", size_bytes=100, expires_in=expires_in
    )

    url = urlsplit(signed_upload.url)
    query = parse_qs(url.query)
    assert (url.netloc, url.path) == ("s3.localhost:9050", "/media-private/u1/f1/original.jpg")
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-SignedHeaders"] == ["content-length;content-type;host;if-none-match"]
    assert query["X-Amz-Expires"] == ["900"]
    assert signed_upload.required_headers == (("Content-Type", "image/jpeg"), ("If-None-Match", "*"))
    assert signed_from + expires_in <= signed_upload.expires_at <= dt.datetime.now(dt.UTC) + expires_in


async def test_sign_upload_invalid_parameters_raise_persistent_error(storage: S3ObjectStorage) -> None:
    """Подпись, которую botocore отказался построить, — постоянный сбой: повтор её не исправит."""
    with pytest.raises(ObjectStoragePersistentError):
        await storage.sign_upload(key="", content_type="image/jpeg", size_bytes=100, expires_in=dt.timedelta(minutes=1))


async def test_head_object_returns_size_and_type(storage: S3ObjectStorage, s3_stubber: AioStubber) -> None:
    """HEAD отдаёт размер и тип записанного объекта своего бакета."""
    s3_stubber.add_response(
        method="head_object",
        service_response={"ContentLength": 100, "ContentType": "image/jpeg"},
        expected_params={"Bucket": "media-private", "Key": "u1/f1/original.jpg"},
    )

    assert await storage.head_object("u1/f1/original.jpg") == ObjectInfo(size_bytes=100, content_type="image/jpeg")


async def test_head_object_missing_object_returns_none(storage: S3ObjectStorage, s3_stubber: AioStubber) -> None:
    """Отсутствующий объект — `None`, а не ошибка."""
    s3_stubber.add_client_error(method="head_object", service_error_code="404", http_status_code=404)

    assert await storage.head_object("u1/f1/original.jpg") is None


async def test_get_object_returns_body_and_closes_stream(storage: S3ObjectStorage, s3_stubber: AioStubber) -> None:
    """Объект в пределах лимита читается целиком, поток после чтения закрыт."""
    stream = FakeS3ResponseStream(body=b"abc")
    s3_stubber.add_response(
        method="get_object",
        service_response={"Body": StreamingBody(raw_stream=stream, content_length=3), "ContentLength": 3},
        expected_params={"Bucket": "media-private", "Key": "u1/f1/original.jpg"},
    )

    assert await storage.get_object(key="u1/f1/original.jpg", max_bytes=3) == b"abc"
    assert stream.is_closed


async def test_get_object_over_limit_raises_without_reading_body(
    storage: S3ObjectStorage, s3_stubber: AioStubber
) -> None:
    """Объект больше лимита отвергается по заголовку: тело не читается, поток закрыт."""
    stream = FakeS3ResponseStream(body=b"", error=AssertionError("тело не должно читаться"))
    s3_stubber.add_response(
        method="get_object",
        service_response={"Body": StreamingBody(raw_stream=stream, content_length=101), "ContentLength": 101},
        expected_params={"Bucket": "media-private", "Key": "u1/f1/original.jpg"},
    )

    with pytest.raises(ObjectTooLargeError):
        await storage.get_object(key="u1/f1/original.jpg", max_bytes=100)

    assert stream.is_closed


@pytest.mark.parametrize("error_code", ["NoSuchKey", "NoSuchBucket"])
async def test_get_object_not_found_status_raises_not_found(
    storage: S3ObjectStorage, s3_stubber: AioStubber, error_code: str
) -> None:
    """Любой 404 при чтении — `ObjectNotFoundError`: то же правило, что у HEAD, где кода ошибки нет."""
    s3_stubber.add_client_error(method="get_object", service_error_code=error_code, http_status_code=404)

    with pytest.raises(ObjectNotFoundError):
        await storage.get_object(key="u1/f1/original.jpg", max_bytes=100)


@pytest.mark.parametrize(
    ("stream", "content_length"),
    [
        pytest.param(FakeS3ResponseStream(body=b"", error=ClientPayloadError("обрыв")), 3, id="connection_dropped"),
        pytest.param(FakeS3ResponseStream(body=b"ab"), 3, id="body_shorter_than_header"),
    ],
)
async def test_get_object_broken_body_raises_temporary_error(
    storage: S3ObjectStorage, s3_stubber: AioStubber, stream: FakeS3ResponseStream, content_length: int
) -> None:
    """Оборванное или недочитанное тело — временный сбой: повторное чтение может пройти."""
    s3_stubber.add_response(
        method="get_object",
        service_response={
            "Body": StreamingBody(raw_stream=stream, content_length=content_length),
            "ContentLength": content_length,
        },
        expected_params={"Bucket": "media-private", "Key": "u1/f1/original.jpg"},
    )

    with pytest.raises(ObjectStorageTemporaryError):
        await storage.get_object(key="u1/f1/original.jpg", max_bytes=100)


async def test_put_object_sends_type_and_cache_control(storage: S3ObjectStorage, s3_stubber: AioStubber) -> None:
    """Объект пишется в свой бакет с заданными типом и `Cache-Control`."""
    s3_stubber.add_response(
        method="put_object",
        service_response={},
        expected_params={
            "Bucket": "media-private",
            "Key": "u1/f1/r1/thumb.webp",
            "Body": b"webp",
            "ContentType": "image/webp",
            "CacheControl": "public, max-age=31536000, immutable",
        },
    )

    await storage.put_object(
        key="u1/f1/r1/thumb.webp",
        body=b"webp",
        content_type="image/webp",
        cache_control="public, max-age=31536000, immutable",
    )


async def test_delete_objects_sends_keys_in_batches_of_thousand(
    storage: S3ObjectStorage, s3_stubber: AioStubber
) -> None:
    """Ключи уходят пачками по 1000 — пределу одного `DeleteObjects`."""
    keys = [f"u1/f{index}/original.jpg" for index in range(1001)]
    for batch in (keys[:1000], keys[1000:]):
        s3_stubber.add_response(
            method="delete_objects",
            service_response={},
            expected_params={
                "Bucket": "media-private",
                "Delete": {"Objects": [{"Key": key} for key in batch], "Quiet": True},
            },
        )

    await storage.delete_objects(keys)


async def test_delete_objects_without_keys_sends_nothing(storage: S3ObjectStorage, s3_stubber: AioStubber) -> None:
    """Пустой набор ключей — ни одного запроса к хранилищу."""
    await storage.delete_objects([])


@pytest.mark.parametrize("temporary_code", ["RequestTimeout", "SlowDown", "InternalError", "ServiceUnavailable"])
async def test_delete_objects_failed_keys_with_one_temporary_code_raise_temporary_error(
    storage: S3ObjectStorage, s3_stubber: AioStubber, temporary_code: str
) -> None:
    """Отказ по ключам в ответе 200 с хотя бы одним временным кодом — временный сбой, коды в деталях."""
    s3_stubber.add_response(
        method="delete_objects",
        service_response={
            "Errors": [
                {"Key": "u1/f1/original.jpg", "Code": "AccessDenied", "Message": "Denied"},
                {"Key": "u1/f2/original.jpg", "Code": temporary_code, "Message": "Retry"},
            ]
        },
        expected_params={
            "Bucket": "media-private",
            "Delete": {"Objects": [{"Key": "u1/f1/original.jpg"}, {"Key": "u1/f2/original.jpg"}], "Quiet": True},
        },
    )

    with pytest.raises(ObjectStorageTemporaryError) as error_info:
        await storage.delete_objects(["u1/f1/original.jpg", "u1/f2/original.jpg"])

    assert error_info.value.details == {
        "failed_keys": {"u1/f1/original.jpg": "AccessDenied", "u1/f2/original.jpg": temporary_code}
    }


async def test_delete_objects_failed_keys_without_temporary_code_raise_persistent_error(
    storage: S3ObjectStorage, s3_stubber: AioStubber
) -> None:
    """Отказ по ключам только с постоянными кодами — постоянный сбой: повтор пачки не удалит их."""
    s3_stubber.add_response(
        method="delete_objects",
        service_response={"Errors": [{"Key": "u1/f1/original.jpg", "Code": "AccessDenied", "Message": "Denied"}]},
        expected_params={
            "Bucket": "media-private",
            "Delete": {"Objects": [{"Key": "u1/f1/original.jpg"}], "Quiet": True},
        },
    )

    with pytest.raises(ObjectStoragePersistentError) as error_info:
        await storage.delete_objects(["u1/f1/original.jpg"])

    assert error_info.value.details == {"failed_keys": {"u1/f1/original.jpg": "AccessDenied"}}


@pytest.mark.parametrize(("operation", "call"), _STORAGE_CALLS, ids=[operation for operation, _ in _STORAGE_CALLS])
@pytest.mark.parametrize(
    ("error_code", "status", "error_class"),
    [
        ("Error", 500, ObjectStorageTemporaryError),
        ("Error", 503, ObjectStorageTemporaryError),
        ("Error", 408, ObjectStorageTemporaryError),
        ("Error", 429, ObjectStorageTemporaryError),
        ("RequestTimeout", 400, ObjectStorageTemporaryError),
        ("Error", 400, ObjectStoragePersistentError),
        ("AccessDenied", 403, ObjectStoragePersistentError),
    ],
)
async def test_storage_call_classifies_error_response(
    storage: S3ObjectStorage,
    s3_stubber: AioStubber,
    operation: str,
    call: Callable[[S3ObjectStorage], Awaitable[object]],
    error_code: str,
    status: int,
    error_class: type[Exception],
) -> None:
    """Ответ 5xx, 408, 429 или с временным кодом S3 — временный сбой, остальные отказы — постоянный."""
    s3_stubber.add_client_error(method=operation, service_error_code=error_code, http_status_code=status)

    with pytest.raises(error_class):
        await call(storage)


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda storage: storage.head_object(""), id="head_object"),
        pytest.param(lambda storage: storage.get_object(key="", max_bytes=100), id="get_object"),
        pytest.param(
            lambda storage: storage.put_object(
                key="", body=b"webp", content_type="image/webp", cache_control="no-cache"
            ),
            id="put_object",
        ),
        pytest.param(lambda storage: storage.delete_objects([""]), id="delete_objects"),
    ],
)
async def test_storage_call_rejected_request_raises_persistent_error(
    storage: S3ObjectStorage, call: Callable[[S3ObjectStorage], Awaitable[object]]
) -> None:
    """Запрос, который botocore отверг до отправки (пустой ключ), — постоянный сбой: повтор его не исправит."""
    with pytest.raises(ObjectStoragePersistentError):
        await call(storage)


@pytest.mark.parametrize(
    "call", [call for _, call in _STORAGE_CALLS], ids=[operation for operation, _ in _STORAGE_CALLS]
)
async def test_storage_call_unreachable_storage_raises_temporary_error(
    unreachable_storage: S3ObjectStorage,
    call: Callable[[S3ObjectStorage], Awaitable[object]],
) -> None:
    """Хранилище, до которого не достучаться, — временный сбой."""
    with pytest.raises(ObjectStorageTemporaryError):
        await call(unreachable_storage)
