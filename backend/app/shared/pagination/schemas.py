from typing import Annotated

from pydantic import ConfigDict, Field

from app.shared.schemas.base import CamelModel


class CursorPaginationFields(CamelModel):
    """
    Поля запроса страницы списка (query-параметры).

    Запрос конкретного списка наследуется от него и добавляет свои фильтры. Без ``cursor``
    отдаётся первая страница, дальше — ``nextCursor`` из предыдущего ответа.
    """

    # Курсор — несколько значений ключа сортировки; строка длиннее заведомо не наша.
    cursor: Annotated[str | None, Field(max_length=512)] = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50


class CursorPageFields[ItemT](CamelModel):
    """
    Страница списка в ответе.

    Ответ конкретного списка — наследник с подставленным типом элемента, а не алиас: так у
    схемы в OpenAPI своё имя. ``nextCursor`` = ``null`` — страница последняя.
    """

    model_config = ConfigDict(frozen=True)

    items: tuple[ItemT, ...]
    next_cursor: str | None
