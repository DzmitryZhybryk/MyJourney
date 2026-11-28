from typing import Any

from sqlalchemy import UnaryExpression
from sqlalchemy.orm import InstrumentedAttribute

from app.shared.enums import SortDirectionEnum


def directed_order(*, column: InstrumentedAttribute[Any], direction: SortDirectionEnum) -> UnaryExpression[Any]:
    """
    Строит элемент ``ORDER BY`` для колонки в заданном направлении.

    Размещение ``NULL`` не задаёт: ``NULLS LAST`` вызывающий добавляет только nullable-колонке — на остальных он
    расходится с порядком индекса.

    Scenarios:
        - любой список, где пользователь выбирает направление сортировки

    Args:
        column: Колонка модели, по которой сортируется список
        direction: Направление сортировки

    Returns:
        Колонка с направлением для ``order_by``
    """
    return column.asc() if direction is SortDirectionEnum.ASC else column.desc()
