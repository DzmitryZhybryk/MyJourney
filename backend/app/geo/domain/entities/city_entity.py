from uuid import UUID

from app.geo.domain.enums import LanguageEnum
from app.geo.domain.value_objects import LocalizedNames


class CityEntity:
    """
    Город из газеттира. Только для чтения: газеттир меняет лишь загрузчик датасетов.

    ``city_id`` — наш id города, не ключ поставщика: его можно отдавать наружу и хранить.
    Названия на разных языках — в ``LocalizedNames``.
    """

    def __init__(
        self,
        *,
        city_id: UUID,
        names: LocalizedNames,
        country_code: str,
        latitude: float,
        longitude: float,
        population: int | None,
    ) -> None:
        self.city_id = city_id
        self.names = names
        self.country_code = country_code
        self.latitude = latitude
        self.longitude = longitude
        self.population = population

    def localized_name(self, *, language: LanguageEnum) -> str | None:
        """
        Возвращает собственное имя города на языке ``language`` (без фоллбэка).

        Сервис использует ``None`` как сигнал качества данных: пользователю отдаётся
        город без перевода на его язык — такие города потом бэкфиллятся вручную.

        Scenarios:
            - автокомплит города: лог городов без перевода на язык запроса

        Args:
            language: Запрашиваемый язык

        Returns:
            Имя на ``language`` либо ``None``, если перевода нет
        """
        return self.names.get(language=language)

    def display_name(self, *, language: LanguageEnum) -> str:
        """
        Возвращает отображаемое имя города под ``language`` с фоллбэком на ``name_en``.

        Scenarios:
            - автокомплит города в полях маршрута
            - названия городов на картах, глобусе и в ленте на языке интерфейса

        Args:
            language: Язык отображения

        Returns:
            Имя на ``language``, иначе канонический ``name_en``
        """
        return self.names.display(language=language)
