import base64
import binascii
import json
from collections.abc import Callable, Sequence

from app.shared.pagination.exceptions import InvalidCursorError

type CursorParser = Callable[[str], object]


def encode_cursor(values: Sequence[str]) -> str:
    """
    Упаковывает значения ключа сортировки последней строки страницы в непрозрачный курсор.

    Scenarios:
        - любой список с keyset-пагинацией: подгрузка следующей страницы

    Args:
        values: Значения ключа сортировки строкой, в порядке сортировки

    Returns:
        Курсор следующей страницы
    """
    payload = json.dumps(list(values), separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(*, cursor: str, parsers: Sequence[CursorParser]) -> tuple[object, ...]:
    """
    Распаковывает курсор и переводит каждое значение в свой тип.

    Значений должно быть столько же, сколько парсеров: курсор от другого списка или
    подделанный руками отклоняется, а не уходит в SQL.

    Scenarios:
        - любой список с keyset-пагинацией: подгрузка следующей страницы

    Args:
        cursor: Курсор, полученный от клиента
        parsers: Парсер для каждого значения ключа сортировки, в порядке сортировки

    Returns:
        Значения ключа сортировки в нужных типах

    Raises:
        InvalidCursorError: курсор не разбирается или не подходит к ключу сортировки
    """
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw_values = json.loads(base64.urlsafe_b64decode(padded))
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError() from exc

    if not isinstance(raw_values, list) or not all(isinstance(raw_value, str) for raw_value in raw_values):
        raise InvalidCursorError()

    # strict=True: значений не столько, сколько парсеров, — тоже ValueError.
    try:
        return tuple(parser(raw_value) for parser, raw_value in zip(parsers, raw_values, strict=True))
    except (TypeError, ValueError) as exc:
        raise InvalidCursorError() from exc


def split_page[RowT](
    *,
    rows: Sequence[RowT],
    limit: int,
    cursor_values: Callable[[RowT], Sequence[str]],
) -> tuple[tuple[RowT, ...], str | None]:
    """
    Отрезает страницу от выборки на ``limit + 1`` строк и строит курсор следующей.

    Лишняя строка нужна только чтобы узнать, есть ли продолжение, — на страницу она не идёт.

    Scenarios:
        - любой список с keyset-пагинацией: каждая страница

    Args:
        rows: Строки выборки, запрошенной с лимитом ``limit + 1``
        limit: Размер страницы
        cursor_values: Значения ключа сортировки строки для курсора

    Returns:
        Строки страницы и курсор следующей; ``None``, если страница последняя
    """
    page_rows = tuple(rows[:limit])
    if len(rows) <= limit:
        return page_rows, None

    return page_rows, encode_cursor(cursor_values(page_rows[-1]))
