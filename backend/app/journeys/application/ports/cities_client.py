from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

__all__ = ["CitiesClientPort", "CityLocationResponse"]


@dataclass(frozen=True, slots=True)
class CityLocationResponse:
    """
    Что journeys получает от geo о городе: страну и координаты.

    Свой тип даже при совпадении полей с результатом geo: фиксирует набор полей, который нужен
    journeys, и не пускает изменения схемы geo в код journeys.
    """

    city_id: UUID
    country_code: str
    latitude: float
    longitude: float


class CitiesClientPort(Protocol):
    """Исходящий вызов в geo, справочник городов."""

    async def find_city_locations(self, *, city_ids: Collection[UUID]) -> tuple[CityLocationResponse, ...]:
        """
        Находит страну и координаты городов по id: поездка хранит их из справочника, а не те, что
        прислал клиент.

        Scenarios:
            - добавление поездки
            - правка поездки в ленте «Все путешествия»
            - расстояние нового маршрута при правке поездки

        Args:
            city_ids: Id городов

        Returns:
            Найденные города в произвольном порядке; несуществующих id в ответе нет
        """
        ...
