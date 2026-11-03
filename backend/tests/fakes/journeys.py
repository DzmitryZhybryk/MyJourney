"""
In-memory фейки journeys: репозиторий поверх ``list``/``dict``, UoW с мокнутым commit и клиент к geo.

Каждый фейк реализует соответствующий порт из ``app.journeys.application.ports.*`` — тот же
контракт, что и боевые реализации, поэтому ``ty`` ловит расхождение сигнатур. ``transaction``
у UoW — no-op область (rollback реальной сессии проверяется в integration), ``commit`` —
``AsyncMock`` (``commit_mock``) для проверки факта фиксации. Те же фейки переиспользуются на
api-уровне через ``app.dependency_overrides``.

Выборки городов фейк не вычисляет из поездок, а отдаёт то, что задал тест: их правила (годы,
фильтры, порядок) живут в SQL и проверяются integration-тестами репозитория — пересчёт в
Python продублировал бы их.
"""

from collections.abc import AsyncGenerator, Collection
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

from app.journeys.application.ports.cities_client import CitiesClientPort, CityLocationResponse
from app.journeys.application.ports.journey_repository import (
    JourneyFilters,
    JourneyOrderScope,
    JourneyRepositoryPort,
    MovementConnection,
    VisitedCity,
)
from app.journeys.application.ports.unit_of_work import JourneyUnitOfWorkPort
from app.journeys.domain.entities import JourneyEntity
from app.journeys.domain.enums import TransportTypeEnum
from app.shared.pagination import CursorPage, PageQuery, decode_cursor, split_page


@dataclass(frozen=True, slots=True)
class MovementConnectionQuery:
    """Фильтр одного запроса маршрутов к фейку — чтобы тест проверил, что сервис его передал."""

    user_id: UUID
    transport_types: frozenset[TransportTypeEnum] | None


class FakeJourneyRepository(JourneyRepositoryPort):
    """Фейк хранилища поездок: собирает вставки, выборки городов отдаёт заданными тестом."""

    def __init__(self) -> None:
        self.journeys: list[JourneyEntity] = []
        self.visited_cities_by_user_id: dict[UUID, list[VisitedCity]] = {}
        self.movement_connections_by_user_id: dict[UUID, list[MovementConnection]] = {}
        # С каким фильтром спрашивали маршруты: сам фильтр фейк не применяет (его правило — в SQL).
        self.movement_connection_queries: list[MovementConnectionQuery] = []
        # Поездки, которые транзакция увидит, дождавшись блокировки области: их успела изменить
        # параллельная транзакция. ``None`` — никто не вмешался.
        self.journeys_after_lock: list[JourneyEntity] | None = None

    async def insert_journey(self, journey_entity: JourneyEntity) -> None:
        self.journeys.append(journey_entity)

    async def update_journey_by_id(self, journey_entity: JourneyEntity) -> None:
        """Заменяет поездку с тем же id её текущим состоянием."""
        self.journeys = [
            journey_entity if stored_entity.journey_id == journey_entity.journey_id else stored_entity
            for stored_entity in self.journeys
        ]

    async def find_journey_by_id_and_user_id_for_update(
        self,
        *,
        journey_id: UUID,
        user_id: UUID,
    ) -> JourneyEntity | None:
        """Поездка пользователя по id; блокировать в фейке нечего."""
        return await self.find_journey_by_id_and_user_id(journey_id=journey_id, user_id=user_id)

    async def find_journey_by_id_and_user_id(self, *, journey_id: UUID, user_id: UUID) -> JourneyEntity | None:
        """Поездка пользователя по id, удалённая тоже — как в SQL."""
        return next(
            (
                journey_entity
                for journey_entity in self.journeys
                if journey_entity.journey_id == journey_id and journey_entity.user_id == user_id
            ),
            None,
        )

    async def lock_sort_keys(self, scope: JourneyOrderScope) -> None:
        """Блокировать нечего; заданные ``journeys_after_lock`` подменяют хранилище, как параллельная транзакция."""
        if self.journeys_after_lock is not None:
            self.journeys = self.journeys_after_lock
            self.journeys_after_lock = None

    async def find_last_sort_key(self, scope: JourneyOrderScope) -> str | None:
        """Наибольший ключ среди неудалённых поездок области."""
        return max(self._sort_keys_in_scope(scope), default=None)

    async def find_next_sort_key(self, *, scope: JourneyOrderScope, after_sort_key: str) -> str | None:
        """Ближайший ключ области, больший ``after_sort_key``."""
        return min((key for key in self._sort_keys_in_scope(scope) if key > after_sort_key), default=None)

    async def find_previous_sort_key(self, *, scope: JourneyOrderScope, before_sort_key: str) -> str | None:
        """Ближайший ключ области, меньший ``before_sort_key``."""
        return max((key for key in self._sort_keys_in_scope(scope) if key < before_sort_key), default=None)

    def _sort_keys_in_scope(self, scope: JourneyOrderScope) -> tuple[str, ...]:
        return tuple(
            journey_entity.sort_key
            for journey_entity in self.journeys
            if journey_entity.user_id == scope.user_id
            and journey_entity.traveled_year == scope.traveled_year
            and journey_entity.deleted_at is None
        )

    async def find_journeys_page_by_user_id(
        self,
        *,
        user_id: UUID,
        page: PageQuery,
        filters: JourneyFilters,
    ) -> CursorPage[JourneyEntity]:
        """Страница ленты поверх ``self.journeys``: те же фильтр, порядок и курсор, что в SQL."""
        journey_entities = [
            journey_entity
            for journey_entity in self.journeys
            if journey_entity.user_id == user_id
            and journey_entity.deleted_at is None
            and (filters.year_from is None or journey_entity.traveled_year >= filters.year_from)
            and (filters.year_to is None or journey_entity.traveled_year <= filters.year_to)
            and (filters.transport_types is None or journey_entity.transport_type in filters.transport_types)
        ]
        # Свежий год сверху, внутри года — по ключу порядка.
        journey_entities.sort(key=lambda journey_entity: (-journey_entity.traveled_year, journey_entity.sort_key))
        if page.cursor is not None:
            # Парсеры (int, str) гарантируют типы значений, decode_cursor отдаёт их как object.
            cursor_year, cursor_sort_key = cast(
                typ=tuple[int, str],
                val=decode_cursor(cursor=page.cursor, parsers=(int, str)),
            )
            journey_entities = [
                journey_entity
                for journey_entity in journey_entities
                if (-journey_entity.traveled_year, journey_entity.sort_key) > (-cursor_year, cursor_sort_key)
            ]

        page_entities, next_cursor = split_page(
            rows=journey_entities,
            limit=page.limit,
            cursor_values=lambda journey_entity: (str(journey_entity.traveled_year), journey_entity.sort_key),
        )
        return CursorPage(items=page_entities, next_cursor=next_cursor)

    async def find_journey_years_by_user_id(self, user_id: UUID) -> tuple[int, ...]:
        """Годы неудалённых поездок пользователя из ``self.journeys``, по возрастанию."""
        return tuple(
            sorted(
                {
                    journey_entity.traveled_year
                    for journey_entity in self.journeys
                    if journey_entity.user_id == user_id and journey_entity.deleted_at is None
                }
            )
        )

    async def find_visited_cities_by_user_id(self, *, user_id: UUID) -> tuple[VisitedCity, ...]:
        return tuple(self.visited_cities_by_user_id.get(user_id, ()))

    async def find_movement_connections_by_user_id(
        self,
        *,
        user_id: UUID,
        transport_types: Collection[TransportTypeEnum] | None,
    ) -> tuple[MovementConnection, ...]:
        self.movement_connection_queries.append(
            MovementConnectionQuery(
                user_id=user_id,
                transport_types=frozenset(transport_types) if transport_types is not None else None,
            )
        )
        return tuple(self.movement_connections_by_user_id.get(user_id, ()))


class FakeJourneyUnitOfWork(JourneyUnitOfWorkPort):
    """In-memory UoW journeys: фейк-репозиторий + мокнутый ``commit`` и no-op ``transaction``."""

    def __init__(self, *, journey_repository: JourneyRepositoryPort) -> None:
        self.journey_repository = journey_repository
        self.commit_mock = AsyncMock()
        self.transactions_started = 0

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        self.transactions_started += 1
        yield

    async def commit(self) -> None:
        await self.commit_mock()


class FakeCitiesClient(CitiesClientPort):
    """
    Фейк клиента journeys → geo: хранит города справочника и записывает вызовы.

    Найденные города отдаёт в порядке хранения, а не запроса — как geo, у которого порядок
    произвольный; тест может переставить ``locations``, чтобы проверить сопоставление по id.
    """

    def __init__(self, *, locations: Collection[CityLocationResponse] = ()) -> None:
        self.locations = {location.city_id: location for location in locations}
        self.calls: list[tuple[UUID, ...]] = []

    async def find_city_locations(self, *, city_ids: Collection[UUID]) -> tuple[CityLocationResponse, ...]:
        self.calls.append(tuple(city_ids))
        return tuple(location for city_id, location in self.locations.items() if city_id in city_ids)
