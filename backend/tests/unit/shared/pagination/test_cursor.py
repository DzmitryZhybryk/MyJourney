"""
Unit-тесты курсора keyset-пагинации: упаковка ключа сортировки, разбор курсора от клиента и
отрезание страницы от выборки на ``limit + 1`` строк.

Курсор приходит от клиента, поэтому главное — что любой испорченный или чужой курсор
превращается в ``InvalidCursorError``, а не долетает до SQL и не роняет запрос в 500.
"""

import base64
import datetime as dt
from uuid import UUID

import pytest

from app.shared.pagination import InvalidCursorError, decode_cursor, encode_cursor, split_page

_PARSERS = (dt.date.fromisoformat, dt.datetime.fromisoformat, UUID)


def test_decode_cursor_restores_encoded_values_with_their_types() -> None:
    """Курсор разбирается обратно в те же значения ключа, микросекунды и таймзона не теряются."""
    sort_date = dt.date(year=2019, month=5, day=1)
    created_at = dt.datetime(year=2024, month=3, day=2, hour=10, minute=4, second=5, microsecond=678, tzinfo=dt.UTC)
    row_id = UUID("6f1c0d6e-0f4e-4d5b-9a51-2f6b1c3d4e5f")
    cursor = encode_cursor([sort_date.isoformat(), created_at.isoformat(), str(row_id)])

    assert decode_cursor(cursor=cursor, parsers=_PARSERS) == (sort_date, created_at, row_id)


def test_encode_cursor_is_url_safe_without_padding() -> None:
    """Курсор уходит в query-параметр: только url-safe символы и без ``=``-паддинга."""
    cursor = encode_cursor(["2019-01-01", "??>>"])

    assert "=" not in cursor
    assert set(cursor) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


@pytest.mark.parametrize(
    "cursor",
    [
        pytest.param("!!!", id="not-base64"),
        pytest.param(base64.urlsafe_b64encode(b"\xff\xfe").decode(), id="not-utf8"),
        pytest.param(base64.urlsafe_b64encode(b"{not json").decode(), id="not-json"),
        pytest.param(base64.urlsafe_b64encode(b'{"sort_date": "2019-01-01"}').decode(), id="object-not-list"),
        pytest.param(
            base64.urlsafe_b64encode(b'["2019-01-01", "2024-01-01T00:00:00+00:00", 7]').decode(),
            id="non-string-value",
        ),
        pytest.param(encode_cursor(["2019-01-01"]), id="too-few-values"),
        pytest.param(
            encode_cursor(["2019-01-01", "2024-01-01T00:00:00+00:00", "6f1c0d6e-0f4e-4d5b-9a51-2f6b1c3d4e5f", "x"]),
            id="too-many-values",
        ),
        pytest.param(
            encode_cursor(["2019-13-45", "2024-01-01T00:00:00+00:00", "6f1c0d6e-0f4e-4d5b-9a51-2f6b1c3d4e5f"]),
            id="invalid-date",
        ),
        pytest.param(encode_cursor(["2019-01-01", "2024-01-01T00:00:00+00:00", "not-a-uuid"]), id="invalid-uuid"),
    ],
)
def test_decode_cursor_broken_or_foreign_cursor_raises_invalid_cursor(cursor: str) -> None:
    """Любой испорченный или не подходящий к ключу курсор — ``invalid_cursor``, а не 500."""
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor=cursor, parsers=_PARSERS)


def test_split_page_with_extra_row_returns_page_and_cursor_of_its_last_row() -> None:
    """Лишняя строка отбрасывается, курсор строится по последней строке страницы, а не по лишней."""
    rows, next_cursor = split_page(rows=[1, 2, 3], limit=2, cursor_values=lambda row: [str(row)])

    assert rows == (1, 2)
    assert next_cursor is not None
    assert decode_cursor(cursor=next_cursor, parsers=(int,)) == (2,)


@pytest.mark.parametrize("row_count", [0, 1, 2])
def test_split_page_without_extra_row_is_last_page(row_count: int) -> None:
    """Строк не больше лимита — страница последняя, курсора нет."""
    all_rows = list(range(row_count))

    rows, next_cursor = split_page(rows=all_rows, limit=2, cursor_values=lambda row: [str(row)])

    assert rows == tuple(all_rows)
    assert next_cursor is None
