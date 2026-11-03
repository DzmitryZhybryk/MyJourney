"""Unit-тесты общих полей запроса страницы: значения по умолчанию и границы ``limit`` и ``cursor``."""

import pytest
from pydantic import ValidationError

from app.shared.pagination.schemas import CursorPaginationFields


def test_cursor_pagination_fields_without_params_asks_first_page_of_default_size() -> None:
    """Без параметров — первая страница (курсора нет) из 50 строк."""
    pagination = CursorPaginationFields.model_validate({})

    assert pagination.cursor is None
    assert pagination.limit == 50


@pytest.mark.parametrize("limit", [1, 100])
def test_cursor_pagination_fields_accepts_limit_on_bounds(limit: int) -> None:
    """Границы размера страницы включительно: 1 и 100."""
    assert CursorPaginationFields.model_validate({"limit": limit}).limit == limit


@pytest.mark.parametrize("limit", [0, 101])
def test_cursor_pagination_fields_rejects_limit_out_of_bounds(limit: int) -> None:
    """Размер страницы вне 1..100 отклоняется на границе запроса."""
    with pytest.raises(ValidationError, match="limit"):
        CursorPaginationFields.model_validate({"limit": limit})


def test_cursor_pagination_fields_rejects_too_long_cursor() -> None:
    """Курсор длиннее 512 символов заведомо не наш — отклоняется до разбора."""
    with pytest.raises(ValidationError, match="cursor"):
        CursorPaginationFields.model_validate({"cursor": "a" * 513})
