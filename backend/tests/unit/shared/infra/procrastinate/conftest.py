"""Фикстуры unit-тестов вертикали procrastinate."""

import pytest
from procrastinate.jobs import Job


@pytest.fixture
def failed_job() -> Job:
    """Задача, упавшая на первом запуске: повторов ещё не было."""
    return Job(
        id=7,
        queue="default",
        lock=None,
        queueing_lock=None,
        task_name="some_task",
        task_kwargs={},
    )
