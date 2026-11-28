from collections.abc import AsyncIterator, Callable

import pytest

from app.shared.infra.email.resend_client import ResendClient
from app.shared.infra.http.config import HTTPClientConfig


@pytest.fixture
async def make_resend_client() -> AsyncIterator[Callable[..., ResendClient]]:
    """Фабрика ``ResendClient``; звать после ``install_mock_transport``, каждый клиент закрывается в teardown."""
    clients: list[ResendClient] = []

    def _make(*, base_url: str, default_from: str) -> ResendClient:
        client = ResendClient(config=HTTPClientConfig(base_url=base_url), default_from=default_from)
        clients.append(client)
        return client

    yield _make

    for client in clients:
        await client.aclose()
