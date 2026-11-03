from datetime import UTC, datetime, timedelta

import pytest
from procrastinate import JobContext
from structlog.testing import capture_logs

from app.auth.infra.tasks import send_verification_email
from app.shared.exceptions import TemporaryError
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


@pytest.mark.parametrize(
    ("error", "is_retried"),
    [
        (ExternalAPITemporaryError(method="POST", url="u", status=503, message="m"), True),
        (TemporaryError(), True),
        (ExternalAPIPersistentError(method="POST", url="u", status=400, message="m"), False),
    ],
)
def test_send_verification_email_retries_any_temporary_error(
    job_context: JobContext, error: Exception, is_retried: bool
) -> None:
    """Повтор задачи — на любой временный сбой, а не только HTTP-провайдера; постоянный не повторяется."""
    retry_strategy = send_verification_email.retry_strategy
    assert retry_strategy is not None

    decision = retry_strategy.get_retry_decision(exception=error, job=job_context.job)

    assert (decision is not None) is is_retried


def test_send_verification_email_retries_after_provider_delay(job_context: JobContext) -> None:
    """Провайдер назвал срок — повтор не раньше него, а не по своей короткой паузе."""
    retry_strategy = send_verification_email.retry_strategy
    assert retry_strategy is not None
    error = ExternalAPITemporaryError(
        method="POST", url="u", status=429, message="m", retry_after=timedelta(seconds=60)
    )

    before = datetime.now(tz=UTC)
    decision = retry_strategy.get_retry_decision(exception=error, job=job_context.job)
    after = datetime.now(tz=UTC)

    assert decision is not None
    assert decision.retry_at is not None
    assert before + timedelta(seconds=60) <= decision.retry_at <= after + timedelta(seconds=60)


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
