from app.geo.domain.enums import LanguageEnum
from tests.builders import make_city


def test_localized_name_missing_translation_returns_none() -> None:
    """Без перевода на язык — ``None``: по нему сервис замечает дыру в данных."""
    city_entity = make_city(en="Mostar", ru=None)

    assert city_entity.localized_name(LanguageEnum.RU) is None


def test_display_name_resolves_under_language_with_fallback() -> None:
    """Имя на языке запроса, иначе на en."""
    city_entity = make_city(en="Moscow", ru="Москва")

    assert city_entity.display_name(LanguageEnum.RU) == "Москва"
    assert city_entity.display_name(LanguageEnum.EN) == "Moscow"
