"""Стратегия повторов фоновой задачи, которая слушает срок, названный внешней зависимостью."""

import math
from datetime import timedelta
from typing import ClassVar

from procrastinate import RetryDecision, RetryStrategy
from procrastinate.jobs import Job

from app.shared.exceptions import TemporaryError
from app.shared.logging import get_logger

logger = get_logger(__name__)


class RetryAfterStrategy(RetryStrategy):
    """
    `RetryStrategy` procrastinate, которая повторяет задачу не раньше срока, названного зависимостью.

    Повторять ли и с какой паузой, решает родитель по своим параметрам. Если задача упала на `TemporaryError` с
    `retry_after`, время повтора берётся из него. Срок длиннее `_MAX_RETRY_AFTER` значит долгий сбой — задача не
    повторяется; подкласс переопределяет потолок.
    """

    _MAX_RETRY_AFTER: ClassVar[timedelta] = timedelta(minutes=5)

    def get_retry_decision(self, *, exception: BaseException, job: Job) -> RetryDecision | None:
        """
        Решает, повторить ли упавшую задачу и когда.

        Scenarios:
            - фоновая задача упала на вызове провайдера, который может сказать, когда повторить

        Args:
            exception: Исключение, которым упала задача
            job: Упавшая задача

        Returns:
            Когда повторить, или `None`, если не повторять
        """
        decision = super().get_retry_decision(exception=exception, job=job)
        retry_after = exception.retry_after if isinstance(exception, TemporaryError) else None
        if decision is None or retry_after is None:
            return decision

        if retry_after > self._MAX_RETRY_AFTER:
            logger.warning(
                "procrastinate.retry.retry_after_exceeds_limit",
                task_name=job.task_name,
                job_id=job.id,
                retry_after_seconds=retry_after.total_seconds(),
                max_retry_after_seconds=self._MAX_RETRY_AFTER.total_seconds(),
            )
            return None

        return RetryDecision(retry_in={"seconds": math.ceil(retry_after.total_seconds())})
