"""
Guard-тест кодов ошибок: ``code`` — идентификатор во внешнем контракте, фронт маппит его в текст.

Лист без собственного ``code`` молча уходит наружу с кодом категории или семейства, а два листа с
одним кодом фронт не различит. Ни линтер, ни типизация этого не видят.
"""

from collections import defaultdict

from app.journeys.exceptions import JourneyDateInFutureError
from app.media.exceptions import ObjectNotFoundError
from app.shared.exceptions import AppError
from app.shared.infra.jwt.exceptions import InvalidAccessTokenError


def test_app_error_leaves_include_known_leaves_of_every_kind(app_error_leaves: tuple[type[AppError], ...]) -> None:
    """Обнаружение находит листья домена, адаптера без роутера и shared-пакета, а не пустой список."""
    assert JourneyDateInFutureError in app_error_leaves
    assert ObjectNotFoundError in app_error_leaves
    assert InvalidAccessTokenError in app_error_leaves


def test_app_error_leaves_define_own_code(app_error_leaves: tuple[type[AppError], ...]) -> None:
    """Каждый лист объявляет свой code, а не наследует его от категории или семейства."""
    without_own_code = [f"{cls.__module__}.{cls.__qualname__}" for cls in app_error_leaves if "code" not in vars(cls)]

    assert without_own_code == []


def test_app_error_leaf_codes_are_unique(app_error_leaves: tuple[type[AppError], ...]) -> None:
    """Никакие два листа не делят один code."""
    classes_by_code: defaultdict[str, list[str]] = defaultdict(list)
    for cls in app_error_leaves:
        classes_by_code[cls.code].append(f"{cls.__module__}.{cls.__qualname__}")

    duplicates = {code: names for code, names in classes_by_code.items() if len(names) > 1}

    assert duplicates == {}
