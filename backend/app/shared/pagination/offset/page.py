from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OffsetPageQuery:
    """
    Какую страницу списка отдать: номер (с 1) и её размер.

    Входит полем в команду списка рядом с её фильтрами.
    """

    page: int
    limit: int


@dataclass(frozen=True, slots=True)
class OffsetPage[ItemT]:
    """Страница списка и число всех строк под фильтром; страница за концом списка — пустые ``items``."""

    items: tuple[ItemT, ...]
    total: int
