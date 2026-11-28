"""Фикстуры unit-тестов вертикали procrastinate."""

import pytest
from procrastinate.jobs import Job

from tests.builders import make_job


@pytest.fixture
def failed_job() -> Job:
    """Задача, упавшая на первом запуске: повторов ещё не было."""
    return make_job(job_id=7)
