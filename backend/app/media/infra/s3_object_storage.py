import datetime as dt
from collections.abc import Collection
from http import HTTPStatus
from itertools import batched
from typing import TYPE_CHECKING, ClassVar, Final

from aiohttp import ClientError as AiohttpClientError
from botocore.exceptions import BotoCoreError, ClientError, IncompleteReadError
from botocore.exceptions import ConnectionError as BotocoreConnectionError
from botocore.exceptions import HTTPClientError as BotocoreHTTPClientError

from app.media.application.ports.private_storage import ObjectInfo, PrivateStoragePort, SignedUpload
from app.media.application.ports.public_storage import PublicStoragePort
from app.media.exceptions import (
    ObjectNotFoundError,
    ObjectStorageError,
    ObjectStoragePersistentError,
    ObjectStorageTemporaryError,
    ObjectTooLargeError,
)
from app.shared.types import DictStrAny

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client

# Обрыв тела aiobotocore не переводит в ошибку botocore — приходит исключение aiohttp.
_SDK_ERRORS: Final = (ClientError, BotoCoreError, AiohttpClientError)
_TEMPORARY_SDK_ERRORS: Final = (
    BotocoreConnectionError,
    BotocoreHTTPClientError,
    IncompleteReadError,
    AiohttpClientError,
)
_TEMPORARY_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {"RequestTimeout", "SlowDown", "InternalError", "ServiceUnavailable"}
)
_TEMPORARY_CLIENT_ERROR_STATUSES: Final[frozenset[HTTPStatus]] = frozenset(
    {HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.TOO_MANY_REQUESTS}
)


class S3ObjectStorage(PrivateStoragePort, PublicStoragePort):
    """
    Один бакет S3-совместимого хранилища.

    Реализует порты и приватного, и публичного бакета: какой из них видит сервис, решает сборка.
    """

    _DELETE_OBJECTS_MAX_KEYS: ClassVar[int] = 1000

    def __init__(self, *, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def sign_upload(
        self,
        *,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_in: dt.timedelta,
    ) -> SignedUpload:
        signed_at = dt.datetime.now(dt.UTC)
        required_headers = _signed_upload_headers(content_type=content_type)
        try:
            url = await self._client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": key,
                    "ContentType": required_headers["Content-Type"],
                    "ContentLength": size_bytes,
                    "IfNoneMatch": required_headers["If-None-Match"],
                },
                ExpiresIn=int(expires_in.total_seconds()),
            )
        except _SDK_ERRORS as error:
            raise _to_storage_error(error=error, details={"key": key}) from error

        return SignedUpload(
            url=url,
            expires_at=signed_at + expires_in,
            required_headers=tuple(required_headers.items()),
        )

    async def head_object(self, key: str) -> ObjectInfo | None:
        try:
            response = await self._client.head_object(Bucket=self._bucket, Key=key)
        except _SDK_ERRORS as error:
            if _is_not_found(error):
                return None

            raise _to_storage_error(error=error, details={"key": key}) from error

        return ObjectInfo(size_bytes=response["ContentLength"], content_type=response.get("ContentType"))

    async def get_object(self, *, key: str, max_bytes: int) -> bytes:
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=key)
        except _SDK_ERRORS as error:
            if _is_not_found(error):
                raise ObjectNotFoundError(details={"key": key}) from error

            raise _to_storage_error(error=error, details={"key": key}) from error

        async with response["Body"] as body:
            if response["ContentLength"] > max_bytes:
                raise ObjectTooLargeError(details={"key": key, "max_bytes": max_bytes})

            try:
                return await body.read()
            except _SDK_ERRORS as error:
                raise _to_storage_error(error=error, details={"key": key}) from error

    async def put_object(self, *, key: str, body: bytes, content_type: str, cache_control: str) -> None:
        try:
            await self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                CacheControl=cache_control,
            )
        except _SDK_ERRORS as error:
            raise _to_storage_error(error=error, details={"key": key}) from error

    async def delete_objects(self, keys: Collection[str]) -> None:
        for batch in batched(iterable=keys, n=self._DELETE_OBJECTS_MAX_KEYS):
            try:
                response = await self._client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
                )
            except _SDK_ERRORS as error:
                raise _to_storage_error(error=error, details={"keys": batch}) from error

            # Отказ по отдельным ключам приходит в теле ответа 200, а не исключением, и статуса у него нет —
            # только код. Повтор пачки безопасен, поэтому хватает одного временного кода среди отказов.
            failed_keys = {error.get("Key"): error.get("Code") for error in response.get("Errors", ())}
            if failed_keys:
                error_class = (
                    ObjectStorageTemporaryError
                    if any(code in _TEMPORARY_ERROR_CODES for code in failed_keys.values())
                    else ObjectStoragePersistentError
                )
                raise error_class(details={"failed_keys": failed_keys})


def _signed_upload_headers(*, content_type: str) -> dict[str, str]:
    return {"Content-Type": content_type, "If-None-Match": "*"}


# 404 приходит и на пропавший бакет, а у ответа HEAD нет тела с кодом ошибки — пропавший бакет от
# пропавшего объекта там неотличим. GET судит по тому же правилу, чтобы «нет объекта» значило одно и то же.
def _is_not_found(error: Exception) -> bool:
    return isinstance(error, ClientError) and _status_of(error) == HTTPStatus.NOT_FOUND


def _to_storage_error(*, error: Exception, details: DictStrAny) -> ObjectStorageError:
    error_class = ObjectStorageTemporaryError if _is_temporary(error) else ObjectStoragePersistentError
    return error_class(details={**details, **_describe_cause(error)})


def _describe_cause(error: Exception) -> DictStrAny:
    if isinstance(error, ClientError):
        return {"s3_error_code": error.response.get("Error", {}).get("Code"), "s3_status": _status_of(error)}

    return {"sdk_error": type(error).__name__}


def _is_temporary(error: Exception) -> bool:
    if isinstance(error, ClientError):
        status = _status_of(error)
        return (
            status >= HTTPStatus.INTERNAL_SERVER_ERROR
            or status in _TEMPORARY_CLIENT_ERROR_STATUSES
            or error.response.get("Error", {}).get("Code") in _TEMPORARY_ERROR_CODES
        )

    return isinstance(error, _TEMPORARY_SDK_ERRORS)


def _status_of(error: ClientError) -> int:
    return error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
