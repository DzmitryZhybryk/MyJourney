import json
from collections.abc import Callable
from typing import Final

import httpx
import pytest

from app.shared.infra.email.resend_client import ResendClient
from app.shared.infra.email.schemas import EmailMessage
from app.shared.infra.http.exceptions import ExternalAPIPersistentError

_BASE_URL: Final[str] = "https://api.resend.test"
_FROM: Final[str] = "noreply@app.test"

type _InstallTransport = Callable[[Callable[[httpx.Request], httpx.Response]], None]


async def test_send_posts_email_payload_to_resend(
    install_mock_transport: _InstallTransport,
    make_resend_client: Callable[..., ResendClient],
) -> None:
    """POST ``/emails`` с from из конфига, to списком и отрендеренными html и text."""
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "email-1"})

    install_mock_transport(handler)

    await make_resend_client(base_url=_BASE_URL, default_from=_FROM).send(
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


async def test_send_client_error_raises_persistent_error(
    install_mock_transport: _InstallTransport,
    make_resend_client: Callable[..., ResendClient],
) -> None:
    """4xx от Resend пробрасывается как ``ExternalAPIPersistentError``: повтор не поможет."""
    install_mock_transport(lambda request: httpx.Response(422, json={"message": "invalid recipient"}))

    with pytest.raises(ExternalAPIPersistentError):
        await make_resend_client(base_url=_BASE_URL, default_from=_FROM).send(
            EmailMessage(to="bad", subject="s", html="h", text="t")
        )
