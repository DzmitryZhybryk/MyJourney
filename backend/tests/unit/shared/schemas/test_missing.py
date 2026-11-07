from pydantic.experimental.missing_sentinel import MISSING

from app.shared.schemas.missing import none_if_missing


def test_none_if_missing_missing_returns_none() -> None:
    """Неприсланное поле (MISSING) превращается в None."""
    assert none_if_missing(MISSING) is None


def test_none_if_missing_value_passes_through_including_falsy() -> None:
    """Присланное значение возвращается как есть, в том числе «ложное» (False, пустая строка)."""
    assert none_if_missing("Alice") == "Alice"
    assert none_if_missing(False) is False
    assert none_if_missing("") == ""
