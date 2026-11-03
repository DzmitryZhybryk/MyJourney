"""
ResendClient — реализация EmailTransportPort поверх HTTP API Resend.

Использует общий BaseHTTPClient (httpx) — без resend-sdk: тот синхронный,
а вся отправка идёт из async-контекста. Ошибки клиента мапятся через
BaseHTTPClient в ExternalAPI*Error, по которым procrastinate решает retry/fail.
"""

from app.shared.infra.email.schemas import EmailMessage
from app.shared.infra.http.client import BaseHTTPClient
from app.shared.infra.http.config import HTTPClientConfig


class ResendClient(BaseHTTPClient):
    """
    HTTP-клиент к Resend API.

    Реализует EmailTransportPort (structural typing — Protocol).
    """

    def __init__(self, *, config: HTTPClientConfig, default_from: str) -> None:
        """
        Инициализирует клиент.

        Args:
            config: HTTP-конфиг с base_url Resend и Authorization-заголовком.
            default_from: From-адрес инстанса клиента (RESEND_FROM_EMAIL).
        """
        super().__init__(config=config)
        self._default_from = default_from

    async def send(self, *, message: EmailMessage) -> None:
        """
        Отправляет письмо через Resend.

        Args:
            message: Готовое сообщение с отрендеренным телом.

        Raises:
            ExternalAPITemporaryError: временный сбой Resend — кандидат на retry.
            ExternalAPIPersistentError: постоянный сбой — без retry.
        """
        await self.post(
            endpoint="/emails",
            json={
                "from": self._default_from,
                "to": [message.to],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            },
        )
