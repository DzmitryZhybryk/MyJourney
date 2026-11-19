from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from app.geo.domain.entities import CityEntity

__all__ = ["CityRepositoryPort"]


class CityRepositoryPort(Protocol):
    """Контракт read-only поиска городов по газеттиру, на который опирается application-слой."""

    async def search_cities_by_name(self, *, search_text: str, limit: int) -> tuple[CityEntity, ...]:
        """
        Ищет города по имени (en/ru), отсортированные по убыванию населения.

        Матч идёт по ПРЕФИКСУ имени (``search_text`` в начале), а не по подстроке:
        'york' не найдёт 'New York'. Это контракт метода, на который опирается вызывающий.

        Scenarios:
            - автокомплит города в полях маршрута «Откуда» и «Куда»

        Args:
            search_text: Начало имени для поиска. Репозиторий экранирует
                LIKE-метасимволы (``%`` ``_`` ``\\``) перед подстановкой в паттерн.
            limit: Максимум кандидатов в выдаче

        Returns:
            Города, отсортированные по убыванию населения
        """
        ...

    async def find_cities_by_ids(self, *, city_ids: Collection[UUID]) -> tuple[CityEntity, ...]:
        """
        Находит города по id; несуществующие id пропускаются.

        Scenarios:
            - названия городов на картах, глобусе и в ленте на языке интерфейса
            - домен, который принимает id городов извне и хранит у себя их страну и координаты

        Args:
            city_ids: Id городов

        Returns:
            Найденные города в произвольном порядке
        """
        ...
