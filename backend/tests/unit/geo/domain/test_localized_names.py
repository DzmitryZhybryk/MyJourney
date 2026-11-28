from app.geo.domain.enums import LanguageEnum
from app.geo.domain.value_objects import LocalizedNames


def test_get_returns_name_in_language() -> None:
    """Имя отдаётся на запрошенном языке."""
    names = LocalizedNames(en="Moscow", ru="Москва")

    assert names.get(LanguageEnum.EN) == "Moscow"
    assert names.get(LanguageEnum.RU) == "Москва"


def test_get_missing_translation_returns_none() -> None:
    """Нет перевода → ``None``: сигнал отсутствия, а не фоллбэк на en."""
    names = LocalizedNames(en="Mostar")

    assert names.get(LanguageEnum.RU) is None


def test_display_missing_translation_falls_back_to_en() -> None:
    """Нет перевода → каноническое имя на en."""
    names = LocalizedNames(en="Mostar")

    assert names.display(LanguageEnum.RU) == "Mostar"
    assert names.display(LanguageEnum.EN) == "Mostar"
