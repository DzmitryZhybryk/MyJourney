"""Unit-тесты базовых исключений: признак серверного сбоя у категории и сообщение ``InvariantViolationError``."""

import pytest

from app.shared.exceptions import ErrorCategoryEnum, InvariantViolationError
from app.shared.fractional_index.exceptions import InvalidFractionalKeyError


def test_error_category_is_server_fault_only_for_temporary_and_internal() -> None:
    """Серверный сбой — временный сбой зависимости и внутренняя ошибка; остальные категории — ошибка запроса."""
    server_faults = {category for category in ErrorCategoryEnum if category.is_server_fault}

    assert server_faults == {ErrorCategoryEnum.TEMPORARY, ErrorCategoryEnum.INTERNAL}


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
