"""
Unit-тесты ``ResendClient.send`` через ``httpx.MockTransport`` (без сети).

Проверяют, что письмо уходит POST'ом на ``/emails`` с правильным payload'ом
(from из конфига, to как список), и что ошибка Resend пробрасывается как
``ExternalAPI*Error`` (через ``BaseHTTPClient``).
"""

import json
from collections.abc import Callable

import httpx
import pytest

from app.shared.infra.email.resend_client import ResendClient
from app.shared.infra.email.schemas import EmailMessage
from app.shared.infra.http.config import HTTPClientConfig
from app.shared.infra.http.exceptions import ExternalAPIPersistentError

_BASE_URL = "https://api.resend.test"
_FROM = "noreply@app.test"

type _InstallTransport = Callable[[Callable[[httpx.Request], httpx.Response]], None]


def _client() -> ResendClient:
    return ResendClient(config=HTTPClientConfig(base_url=_BASE_URL), default_from=_FROM)


async def test_send_posts_email_payload_to_resend(install_mock_transport: _InstallTransport) -> None:
    """``send`` шлёт POST /emails с from из конфига, to как список и отрендеренными html/text."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "email-1"})

    install_mock_transport(handler)

    await _client().send(
        EmailMessage(to="user@example.com", subject="Привет", html="<b>код 123</b>", text="код 123"),
    )

    assert captured["url"] == f"{_BASE_URL}/emails"
    assert captured["method"] == "POST"
    assert captured["payload"] == {
        "from": _FROM,
        "to": ["user@example.com"],
        "subject": "Привет",
        "html": "<b>код 123</b>",
        "text": "код 123",
    }


async def test_send_propagates_persistent_error_on_client_error(
    install_mock_transport: _InstallTransport,
) -> None:
    """4xx от Resend пробрасывается как ``ExternalAPIPersistentError`` (без retry)."""
    install_mock_transport(lambda request: httpx.Response(422, json={"message": "invalid recipient"}))

    with pytest.raises(ExternalAPIPersistentError):
        await _client().send(EmailMessage(to="bad", subject="s", html="h", text="t"))
