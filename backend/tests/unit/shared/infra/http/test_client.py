"""
Unit-тесты ``BaseHTTPClient`` через ``httpx.MockTransport`` (без сети).

Покрывают маппинг ответов внешнего API в ``ExternalAPI*Error``: успех проходит,
таймаут, сетевая ошибка, любой 5xx, 408 и 429 → temporary (кандидат на retry), остальные
4xx → persistent; набор временных 4xx переопределяется подклассом; уровень лога следует
классу ошибки; срок повтора из ``Retry-After`` (и его источник переопределяется подклассом);
плюс извлечение сообщения об ошибке из тела.

Клиент создаётся фабрикой ``make_http_client`` (conftest) — она же закрывает его в
teardown. ``install_mock_transport`` вызывается ДО создания клиента: он патчит
``httpx.AsyncClient`` на mock-транспортный.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from http import HTTPStatus

import httpx
import pytest
from structlog.testing import capture_logs

from app.shared.infra.http.client import BaseHTTPClient
from app.shared.infra.http.exceptions import ExternalAPIError, ExternalAPIPersistentError, ExternalAPITemporaryError

type _InstallTransport = Callable[[Callable[[httpx.Request], httpx.Response]], None]
type _MakeClient = Callable[..., BaseHTTPClient]


async def test_get_success_returns_response(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """Успешный GET (2xx) возвращает httpx-ответ без обёртки в исключение."""
    install_mock_transport(lambda request: httpx.Response(200, json={"ok": True}))
    client = make_http_client()

    response = await client.get("/ping")

    assert response.status_code == 200


async def test_post_success_returns_response(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """Успешный POST (2xx) возвращает httpx-ответ."""
    install_mock_transport(lambda request: httpx.Response(201, json={"id": "1"}))
    client = make_http_client()

    response = await client.post("/items", json={"name": "x"})

    assert response.status_code == 201


async def test_timeout_raises_temporary_error(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """Таймаут запроса → ``ExternalAPITemporaryError`` (кандидат на retry)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)  # noqa: TRY003 — сообщение библиотечного исключения

    install_mock_transport(handler)
    client = make_http_client()

    with pytest.raises(ExternalAPITemporaryError):
        await client.get("/ping")


async def test_network_error_raises_temporary_error(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """Сетевая ошибка → ``ExternalAPITemporaryError`` (кандидат на retry)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)  # noqa: TRY003 — сообщение библиотечного исключения

    install_mock_transport(handler)
    client = make_http_client()

    with pytest.raises(ExternalAPITemporaryError):
        await client.get("/ping")


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504, 599])
async def test_temporary_status_raises_temporary_error(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
    status: int,
) -> None:
    """Любой 5xx, 408 и 429 → ``ExternalAPITemporaryError``: повтор позже может пройти."""
    install_mock_transport(lambda request: httpx.Response(status))
    client = make_http_client()

    with pytest.raises(ExternalAPITemporaryError):
        await client.get("/ping")


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422, 499])
async def test_other_client_error_status_raises_persistent_error(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
    status: int,
) -> None:
    """Остальные 4xx → ``ExternalAPIPersistentError``: тот же запрос не пройдёт и при повторе."""
    install_mock_transport(lambda request: httpx.Response(status))
    client = make_http_client()

    with pytest.raises(ExternalAPIPersistentError):
        await client.get("/ping")


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (409, ExternalAPITemporaryError),
        (429, ExternalAPIPersistentError),
        (503, ExternalAPITemporaryError),
    ],
)
async def test_provider_subclass_overrides_temporary_client_error_statuses(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
    status: int,
    error_class: type[Exception],
) -> None:
    """Подкласс провайдера заменяет набор временных 4xx; любой 5xx остаётся временным."""

    class ConflictRetryingClient(BaseHTTPClient):
        _TEMPORARY_CLIENT_ERROR_STATUSES = frozenset({HTTPStatus.CONFLICT})

    install_mock_transport(lambda request: httpx.Response(status))
    client = make_http_client(client_class=ConflictRetryingClient)

    with pytest.raises(error_class):
        await client.get("/ping")


@pytest.mark.parametrize(
    ("headers", "expected_retry_after"),
    [
        ({"Retry-After": "120"}, timedelta(seconds=120)),
        ({"Retry-After": " 60 "}, timedelta(seconds=60)),
        ({"Retry-After": "0"}, timedelta(0)),
        ({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}, timedelta(0)),
        ({"Retry-After": "Wed, 21 Oct 2015 07:28:00 -0000"}, timedelta(0)),
        ({"Retry-After": "soon"}, None),
        ({"Retry-After": "-5"}, None),
        ({"Retry-After": ""}, None),
        ({"Retry-After": "1" * 20}, None),
        ({"Retry-After": "1" * 5000}, None),
        ({b"Retry-After": "٣٠".encode()}, None),
        ({}, None),
    ],
)
async def test_temporary_error_carries_retry_after_from_header(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
    headers: dict[str, str] | dict[bytes, bytes],
    expected_retry_after: timedelta | None,
) -> None:
    """Срок из ``Retry-After``: секунды как есть, прошедшая дата — ноль, нечитаемое или отсутствующее — ``None``."""
    install_mock_transport(lambda request: httpx.Response(429, headers=headers))
    client = make_http_client()

    with pytest.raises(ExternalAPITemporaryError) as exc_info:
        await client.get("/ping")

    assert exc_info.value.retry_after == expected_retry_after


async def test_temporary_error_retry_after_counts_down_to_http_date(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """``Retry-After`` датой в будущем → срок до неё от текущего момента."""
    retry_at = datetime.now(tz=UTC) + timedelta(seconds=120)
    install_mock_transport(
        lambda request: httpx.Response(503, headers={"Retry-After": format_datetime(retry_at, usegmt=True)})
    )
    client = make_http_client()

    with pytest.raises(ExternalAPITemporaryError) as exc_info:
        await client.get("/ping")

    retry_after = exc_info.value.retry_after
    assert retry_after is not None
    assert timedelta(seconds=110) < retry_after <= timedelta(seconds=120)


async def test_provider_subclass_overrides_retry_after_source(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """Подкласс провайдера берёт срок из своего места в ответе — здесь из тела."""

    class BodyRetryAfterClient(BaseHTTPClient):
        def _retry_after(self, response: httpx.Response) -> timedelta | None:
            return timedelta(seconds=response.json()["retry_in"])

    install_mock_transport(lambda request: httpx.Response(429, json={"retry_in": 30}))
    client = make_http_client(client_class=BodyRetryAfterClient)

    with pytest.raises(ExternalAPITemporaryError) as exc_info:
        await client.get("/ping")

    assert exc_info.value.retry_after == timedelta(seconds=30)


@pytest.mark.parametrize(("status", "expected_level"), [(503, "warning"), (400, "error")])
async def test_error_response_log_level_follows_error_class(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
    status: int,
    expected_level: str,
) -> None:
    """Строка лога ответа с ошибкой: временный сбой — WARNING, постоянный — ERROR."""
    install_mock_transport(lambda request: httpx.Response(status))
    client = make_http_client()

    with capture_logs() as logs, pytest.raises(ExternalAPIError):
        await client.get("/ping")

    assert [log["log_level"] for log in logs if log["event"] == "http_client.error_response"] == [expected_level]


async def test_client_error_extracts_message_from_body(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """4xx с телом ``{"message": ...}`` → persistent с этим сообщением и статусом."""
    install_mock_transport(lambda request: httpx.Response(404, json={"message": "ресурс не найден"}))
    client = make_http_client()

    with pytest.raises(ExternalAPIPersistentError) as exc_info:
        await client.get("/missing")

    assert exc_info.value.status == 404
    assert exc_info.value.message == "ресурс не найден"


async def test_client_error_without_known_keys_falls_back_to_status(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """4xx с телом-словарём без ключей message/detail/error → сообщение-фоллбэк ``HTTP <status>``."""
    install_mock_transport(lambda request: httpx.Response(400, json={"foo": "bar"}))
    client = make_http_client()

    with pytest.raises(ExternalAPIPersistentError) as exc_info:
        await client.get("/bad")

    assert exc_info.value.message == "HTTP 400"
    assert exc_info.value.body == {"foo": "bar"}


async def test_client_error_with_non_json_body_keeps_text(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """4xx с не-JSON телом → тело сохраняется как текст, сообщение-фоллбэк ``HTTP <status>``."""
    install_mock_transport(lambda request: httpx.Response(400, text="upstream said no"))
    client = make_http_client()

    with pytest.raises(ExternalAPIPersistentError) as exc_info:
        await client.get("/bad")

    assert exc_info.value.message == "HTTP 400"
    assert exc_info.value.body == "upstream said no"


async def test_client_error_with_empty_body_has_none_body(
    install_mock_transport: _InstallTransport,
    make_http_client: _MakeClient,
) -> None:
    """4xx с пустым телом → ``body is None`` (пустой текст не превращается в строку)."""
    install_mock_transport(lambda request: httpx.Response(400))
    client = make_http_client()

    with pytest.raises(ExternalAPIPersistentError) as exc_info:
        await client.get("/bad")

    assert exc_info.value.body is None
