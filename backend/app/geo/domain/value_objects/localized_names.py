from app.geo.domain.enums import LanguageEnum


class LocalizedNames:
    """
    Имена объекта газеттира по языкам (value object).

    Группирует разноязычные написания в один тип, чтобы они не болтались отдельными полями
    на сущности. Резолв имени — единый параметризованный (``get`` без фоллбэка / ``display``
    с фоллбэком), а не метод-на-язык: добавить язык = один kwarg конструктора плюс его
    попадание в ``_by_language``.

    Инвариант: ``en`` присутствует всегда — канонический ярлык и фоллбэк для языков без перевода.
    """

    def __init__(self, *, en: str, ru: str | None = None) -> None:
        self._by_language: dict[LanguageEnum, str] = {LanguageEnum.EN: en}
        if ru is not None:
            self._by_language[LanguageEnum.RU] = ru

    def get(self, *, language: LanguageEnum) -> str | None:
        """
        Возвращает собственное имя на языке ``language`` без фоллбэка.

        Scenarios:
            - автокомплит города: лог городов без перевода на язык запроса

        Args:
            language: Запрашиваемый язык

        Returns:
            Имя на ``language`` либо ``None``, если перевода нет
        """
        return self._by_language.get(language)

    def display(self, *, language: LanguageEnum) -> str:
        """
        Возвращает имя под ``language`` с фоллбэком на канонический ``LanguageEnum.EN``.

        Scenarios:
            - автокомплит города в полях маршрута
            - названия городов на картах, глобусе и в ленте на языке интерфейса

        Args:
            language: Язык отображения

        Returns:
            Имя на ``language``, иначе ``en``
        """
        return self._by_language.get(language) or self._by_language[LanguageEnum.EN]
