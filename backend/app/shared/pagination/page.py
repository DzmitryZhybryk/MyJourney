from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageQuery:
    """
    Какую страницу списка отдать: курсор (``None`` — первая страница) и её размер.

    Входит полем в команду списка рядом с её фильтрами.
    """

    cursor: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class CursorPage[ItemT]:
    """Страница списка и курсор следующей; ``next_cursor`` = ``None`` — страница последняя."""

    items: tuple[ItemT, ...]
    next_cursor: str | None
