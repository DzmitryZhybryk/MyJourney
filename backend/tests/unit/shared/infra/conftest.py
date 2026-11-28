"""
``BaseHTTPClient`` создаёт свой ``httpx.AsyncClient`` в ``__init__`` и не даёт подставить транспорт, поэтому
подменяется конструктор ``httpx.AsyncClient``.
"""

from collections.abc import Callable

import httpx
import pytest


@pytest.fixture
def install_mock_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[Callable[[httpx.Request], httpx.Response]], None]:
    """
    Возвращает ``install(handler)``: подменяет ``httpx.AsyncClient`` на mock-транспортный.

    Вызови ``install(handler)`` ДО конструирования клиента. ``handler`` — ``Request -> Response``;
    может бросать httpx-ошибки (``ReadTimeout``, ``ConnectError``) для проверки их маппинга.
    """

    def _install(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        original_async_client = httpx.AsyncClient

        def patched(*, base_url: str = "", **_ignored: object) -> httpx.AsyncClient:
            return original_async_client(transport=httpx.MockTransport(handler), base_url=base_url)

        monkeypatch.setattr(httpx, "AsyncClient", patched)

    return _install
