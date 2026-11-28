"""``make_http_client()`` зовётся после ``install_mock_transport(handler)``: тот подменяет конструктор клиента httpx."""

from collections.abc import AsyncIterator, Callable

import pytest

from app.shared.infra.http.client import BaseHTTPClient
from app.shared.infra.http.config import HTTPClientConfig

_BASE_URL = "https://api.example.test"


@pytest.fixture
async def make_http_client() -> AsyncIterator[Callable[..., BaseHTTPClient]]:
    """
    Возвращает ``make(client_class=BaseHTTPClient)`` — фабрику клиента на тест-``base_url``.

    Каждый созданный клиент регистрируется и закрывается (``aclose``) в teardown,
    поэтому тесту не нужно звать ``aclose`` вручную. ``client_class`` — подкласс
    со своими правилами провайдера, если тест проверяет их.

    Returns:
        Фабрика, возвращающая свежий клиент
    """
    clients: list[BaseHTTPClient] = []

    def _make(client_class: type[BaseHTTPClient] = BaseHTTPClient) -> BaseHTTPClient:
        client = client_class(config=HTTPClientConfig(base_url=_BASE_URL))
        clients.append(client)
        return client

    yield _make

    for client in clients:
        await client.aclose()
