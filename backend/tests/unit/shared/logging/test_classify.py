import logging

import pytest

from app.shared.exceptions.base import InternalError, InvalidInputError, NotFoundError
from app.shared.logging.classify import get_log_level_for_exception, get_status_code_from_exception


@pytest.mark.parametrize(
    ("error", "expected_level"),
    [
        (InternalError(), logging.ERROR),
        (InvalidInputError(), logging.WARNING),
        (ValueError("boom"), logging.ERROR),
    ],
)
def test_get_log_level_for_exception(error: Exception, expected_level: int) -> None:
    """INTERNAL → ERROR, клиентские категории AppError → WARNING, исключения вне AppError → ERROR."""
    assert get_log_level_for_exception(error) == expected_level


def test_get_status_code_delegates_to_resolve() -> None:
    """get_status_code_from_exception делегирует HTTP-резолву категории."""
    assert get_status_code_from_exception(NotFoundError()) == 404
