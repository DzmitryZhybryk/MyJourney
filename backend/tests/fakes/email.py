"""Фейк ``EmailTransportPort``: записывает отправленные письма для state-ассертов."""

from app.shared.infra.email import EmailMessage, EmailTransportPort


class FakeEmailTransport(EmailTransportPort):
    """
    Записывает каждое отправленное письмо в ``sent`` вместо реальной отправки.

    Тест может выставить ``error`` — тогда ``send`` поднимает его вместо записи,
    моделируя сбой транспорта (temporary/persistent для проверки проброса).
    """

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.error: Exception | None = None

    async def send(self, message: EmailMessage) -> None:
        if self.error is not None:
            raise self.error

        self.sent.append(message)
