import pytest
from procrastinate import JobContext
from structlog.testing import capture_logs

from app.auth.infra.tasks import send_verification_email
from app.shared.infra.http.exceptions import ExternalAPIPersistentError, ExternalAPITemporaryError
from tests.fakes import FakeEmailTransport


async def test_send_verification_email_renders_and_sends(
    job_context: JobContext,
    fake_email_transport: FakeEmailTransport,
) -> None:
    """send_verification_email рендерит письмо и отдаёт транспорту: to=email, код в html и text."""
    await send_verification_email(job_context, user_id="user-1", email="user@example.com", code="123456")

    assert len(fake_email_transport.sent) == 1
    message = fake_email_transport.sent[0]
    assert message.to == "user@example.com"
    assert message.subject
    assert "123456" in message.html
    assert "123456" in message.text


async def test_send_verification_email_logs_sending_without_personal_data(
    job_context: JobContext,
    fake_email_transport: FakeEmailTransport,
) -> None:
    """Отправка пишется в лог с user_id; ни адреса, ни кода в строке нет."""
    with capture_logs() as logs:
        await send_verification_email(job_context, user_id="user-1", email="user@example.com", code="123456")

    assert len(fake_email_transport.sent) == 1
    assert logs == [{"event": "auth.verification_email.sent", "user_id": "user-1", "log_level": "info"}]


async def test_send_verification_email_propagates_temporary_error(
    job_context: JobContext,
    fake_email_transport: FakeEmailTransport,
) -> None:
    """temporary-ошибка транспорта пробрасывается (не глотается → сработает retry); письмо не отправлено."""
    fake_email_transport.error = ExternalAPITemporaryError(
        method="POST",
        url="https://api.resend.com/emails",
        status=503,
        message="upstream unavailable",
    )

    with pytest.raises(ExternalAPITemporaryError):
        await send_verification_email(job_context, user_id="user-1", email="user@example.com", code="123456")

    assert fake_email_transport.sent == []


async def test_send_verification_email_propagates_persistent_error(
    job_context: JobContext,
    fake_email_transport: FakeEmailTransport,
) -> None:
    """persistent-ошибка транспорта пробрасывается, не глотается (retry по ней не делается); письмо не отправлено."""
    fake_email_transport.error = ExternalAPIPersistentError(
        method="POST",
        url="https://api.resend.com/emails",
        status=400,
        message="bad request",
    )

    with pytest.raises(ExternalAPIPersistentError):
        await send_verification_email(job_context, user_id="user-1", email="user@example.com", code="123456")

    assert fake_email_transport.sent == []
