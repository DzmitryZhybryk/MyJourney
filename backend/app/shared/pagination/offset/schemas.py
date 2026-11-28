from typing import Annotated

from pydantic import ConfigDict, Field

from app.shared.schemas.base import CamelModel


class OffsetPaginationFields(CamelModel):
    """
    Поля запроса страницы списка с номерами страниц (query-параметры).

    Запрос конкретного списка наследуется от него и добавляет свои фильтры. Без ``page`` отдаётся первая
    страница.
    """

    # Граница держит OFFSET в bigint и отсекает номера, ради которых базе пришлось бы пропустить миллионы строк.
    page: Annotated[int, Field(ge=1, le=10_000)] = 1
    limit: Annotated[int, Field(ge=1, le=100)] = 20


class OffsetPageFields[ItemT](CamelModel):
    """
    Страница списка с номерами страниц в ответе.

    Ответ конкретного списка — наследник с подставленным типом элемента, а не алиас: так у схемы в OpenAPI
    своё имя. ``total`` — число всех строк под фильтром, по нему клиент считает число страниц.
    """

    model_config = ConfigDict(frozen=True)

    items: tuple[ItemT, ...]
    total: int
