"""
Unit-тесты ``RetryAfterStrategy``: решение о повторе — за procrastinate, срок зависимости меняет только время.

Время повтора проверяется окном: ``retry_at`` лежит между моментами до и после вызова плюс ожидаемая пауза.
"""

from datetime import UTC, datetime, timedelta

import pytest
from procrastinate.jobs import Job
from structlog.testing import capture_logs

from app.shared.exceptions import InternalError, TemporaryError
from app.shared.infra.procrastinate.retry import RetryAfterStrategy

_STRATEGY = RetryAfterStrategy(max_attempts=3, wait=10, exponential_wait=2, retry_exceptions={TemporaryError})


@pytest.mark.parametrize(
    ("retry_after", "expected_delay"),
    [
        (None, timedelta(seconds=12)),
        (timedelta(seconds=60), timedelta(seconds=60)),
        (timedelta(seconds=59.2), timedelta(seconds=60)),
        (timedelta(0), timedelta(0)),
        (timedelta(minutes=5), timedelta(minutes=5)),
    ],
)
def test_retry_after_strategy_retries_after_dependency_delay_or_own_backoff(
    failed_job: Job, retry_after: timedelta | None, expected_delay: timedelta
) -> None:
    """Без срока — пауза procrastinate (10 + 2¹ с); со сроком до потолка включительно — срок, округлённый вверх."""
    before = datetime.now(tz=UTC)
    decision = _STRATEGY.get_retry_decision(exception=TemporaryError(retry_after=retry_after), job=failed_job)
    after = datetime.now(tz=UTC)

    assert decision is not None
    assert decision.retry_at is not None
    assert before + expected_delay <= decision.retry_at <= after + expected_delay


def test_retry_after_strategy_gives_up_on_delay_over_limit(failed_job: Job) -> None:
    """Срок длиннее 5 минут — задача не повторяется, причина пишется WARNING'ом."""
    with capture_logs() as logs:
        decision = _STRATEGY.get_retry_decision(
            exception=TemporaryError(retry_after=timedelta(minutes=5, seconds=1)), job=failed_job
        )

    assert decision is None
    assert logs == [
        {
            "event": "procrastinate.retry.retry_after_exceeds_limit",
            "task_name": "some_task",
            "job_id": 7,
            "retry_after_seconds": 301.0,
            "max_retry_after_seconds": 300.0,
            "log_level": "warning",
        }
    ]


def test_retry_after_strategy_keeps_procrastinate_attempt_limit(failed_job: Job) -> None:
    """Повторы кончились — срок зависимости не продлевает их, и WARNING о потолке не пишется."""
    with capture_logs() as logs:
        decision = _STRATEGY.get_retry_decision(
            exception=TemporaryError(retry_after=timedelta(minutes=10)), job=failed_job.evolve(attempts=3)
        )

    assert decision is None
    assert logs == []


@pytest.mark.parametrize("error", [InternalError(), ValueError("boom")])
def test_retry_after_strategy_does_not_retry_other_errors(failed_job: Job, error: Exception) -> None:
    """Исключение вне ``retry_exceptions`` не повторяется."""
    assert _STRATEGY.get_retry_decision(exception=error, job=failed_job) is None
