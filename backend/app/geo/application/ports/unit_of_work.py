from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.geo.application.ports.city_repository import CityRepositoryPort

__all__ = ["GeoUnitOfWorkPort"]


class GeoUnitOfWorkPort(Protocol):
    """
    Контракт транзакционной границы geo, на который опирается ``CityService``.

    Объединяет доступ к репозиторию (через его порт) и транзакционную область
    ``transaction()``. Без ``commit``: сервисы geo справочник только читают, писать им
    нечего — данные газеттира загружает отдельный CLI мимо use case'ов.
    """

    city_repository: CityRepositoryPort

    def transaction(self) -> AbstractAsyncContextManager[None]: ...
