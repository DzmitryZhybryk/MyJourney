import pytest
from pydantic import ValidationError

from app.shared.pagination.offset.schemas import OffsetPaginationFields


def test_offset_pagination_fields_without_params_asks_first_page_of_default_size() -> None:
    """Без параметров — первая страница из 20 строк."""
    pagination = OffsetPaginationFields.model_validate({})

    assert pagination.page == 1
    assert pagination.limit == 20


@pytest.mark.parametrize(("field", "value"), [("page", 1), ("page", 10_000), ("limit", 1), ("limit", 100)])
def test_offset_pagination_fields_accepts_values_on_bounds(field: str, value: int) -> None:
    """Границы включительно: страница 1..10 000, размер 1..100."""
    assert getattr(OffsetPaginationFields.model_validate({field: value}), field) == value


@pytest.mark.parametrize(("field", "value"), [("page", 0), ("page", 10_001), ("limit", 0), ("limit", 101)])
def test_offset_pagination_fields_rejects_values_out_of_bounds(field: str, value: int) -> None:
    """Номер или размер страницы вне границ отклоняется на границе запроса."""
    with pytest.raises(ValidationError, match=field):
        OffsetPaginationFields.model_validate({field: value})
