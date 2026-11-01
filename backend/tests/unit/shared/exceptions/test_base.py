"""Unit-тесты ``InvariantViolationError`` — сообщение из текста класса и переданных значений."""

import pytest

from app.shared.exceptions import InvariantViolationError
from app.shared.fractional_index.exceptions import InvalidFractionalKeyError


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (InvariantViolationError(), "Нарушен инвариант"),
        (InvariantViolationError(key="a0", count=2), "Нарушен инвариант: key='a0', count=2"),
        (InvalidFractionalKeyError(key="a0"), "Некорректный дробный ключ: key='a0'"),
    ],
)
def test_invariant_violation_error_message(error: InvariantViolationError, expected_message: str) -> None:
    """Сообщение — message наследника, к которому дописаны переданные значения как name=repr."""
    assert str(error) == expected_message
