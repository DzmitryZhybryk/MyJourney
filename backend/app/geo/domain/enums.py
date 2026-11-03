from enum import StrEnum


class LanguageEnum(StrEnum):
    """
    Язык отображаемого имени объекта газеттира.

    Закрытое множество поддерживаемых языков газеттира: имена импортируются только
    для ``en``/``ru``. Используется как тип query-параметра ``language`` на границе HTTP
    и как ключ резолва имени в ``LocalizedNames``.
    """

    EN = "en"
    RU = "ru"


class PlaceKindEnum(StrEnum):
    """
    Тип места газеттира: озеро, гора, хребет и т.п.

    Закрытое множество: строка датасета с типом не из этого списка не загружается.
    Новый тип — новый вариант здесь и новая версия датасета.
    """

    RESERVOIR = "reservoir"
    LAKE = "lake"
    VOLCANO = "volcano"
    MOUNTAIN = "mountain"
    MOUNTAIN_RANGE = "mountain_range"
    WATERFALL = "waterfall"
    GLACIER = "glacier"
    MOUNTAIN_PASS = "mountain_pass"  # noqa: S105
    NATIONAL_PARK = "national_park"
    NATURE_RESERVE = "nature_reserve"
