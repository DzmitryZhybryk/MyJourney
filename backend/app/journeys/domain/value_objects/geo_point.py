from uuid import UUID

from app.shared.utils.great_circle import great_circle_km


class GeoPoint:
    """
    Точка маршрута поездки — город из справочника geo.

    Название города здесь не хранится: фронт запрашивает его у geo на нужном языке.
    """

    def __init__(
        self,
        *,
        city_id: UUID,
        country_code: str,
        latitude: float,
        longitude: float,
    ) -> None:
        self._city_id = city_id
        self._country_code = country_code
        self._latitude = latitude
        self._longitude = longitude

    @property
    def city_id(self) -> UUID:
        return self._city_id

    @property
    def country_code(self) -> str:
        return self._country_code

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    def distance_km_to(self, destination: GeoPoint) -> int:
        """
        Считает расстояние маршрута до точки назначения — так его хранит поездка.

        Scenarios:
            - добавление поездки
            - правка поездки в ленте «Все путешествия»
            - расстояние нового маршрута при правке поездки

        Args:
            destination: Точка назначения

        Returns:
            Расстояние по большой окружности, км
        """
        return great_circle_km(
            origin_latitude=self.latitude,
            origin_longitude=self.longitude,
            destination_latitude=destination.latitude,
            destination_longitude=destination.longitude,
        )
