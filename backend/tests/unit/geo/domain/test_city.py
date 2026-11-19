"""Unit-тесты доменных ``LocalizedNames``/``CityEntity`` — резолв имени под язык и фоллбэк на en."""

from uuid import uuid4

from app.geo.domain.entities import CityEntity
from app.geo.domain.enums import LanguageEnum
from app.geo.domain.value_objects import LocalizedNames


def test_localized_names_get_returns_localized_without_fallback() -> None:
    """LocalizedNames.get: возвращает имя на языке, либо None если перевода нет (без фоллбэка)."""
    names = LocalizedNames(en="Moscow", ru="Москва")

    assert names.get(language=LanguageEnum.EN) == "Moscow"
    assert names.get(language=LanguageEnum.RU) == "Москва"


def test_localized_names_get_returns_none_for_missing_translation() -> None:
    """LocalizedNames.get: нет ru-перевода → None (сигнал отсутствия, не фоллбэк)."""
    names = LocalizedNames(en="Mostar")

    assert names.get(language=LanguageEnum.RU) is None


def test_localized_names_display_falls_back_to_en() -> None:
    """LocalizedNames.display: нет перевода на язык → канонический en."""
    names = LocalizedNames(en="Mostar")

    assert names.display(language=LanguageEnum.RU) == "Mostar"
    assert names.display(language=LanguageEnum.EN) == "Mostar"


def test_city_localized_name_signals_missing_translation() -> None:
    """CityEntity.localized_name: без ru-перевода возвращает None — сигнал качества данных для сервиса."""
    city_entity = CityEntity(
        city_id=uuid4(),
        names=LocalizedNames(en="Mostar"),
        country_code="BA",
        latitude=43.3,
        longitude=17.8,
        population=100_000,
    )

    assert city_entity.localized_name(language=LanguageEnum.RU) is None


def test_city_display_name_resolves_under_language_with_fallback() -> None:
    """CityEntity.display_name: отдаёт имя на языке, иначе фоллбэк на en."""
    city_entity = CityEntity(
        city_id=uuid4(),
        names=LocalizedNames(en="Moscow", ru="Москва"),
        country_code="RU",
        latitude=55.75,
        longitude=37.62,
        population=10_000_000,
    )

    assert city_entity.display_name(language=LanguageEnum.RU) == "Москва"
    assert city_entity.display_name(language=LanguageEnum.EN) == "Moscow"
