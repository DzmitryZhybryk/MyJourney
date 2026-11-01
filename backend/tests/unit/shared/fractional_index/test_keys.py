"""Unit-тесты ``generate_key_between`` — дробный ключ строго между соседями."""

import random
import re

import pytest

from app.shared.fractional_index import generate_key_between
from app.shared.fractional_index.exceptions import FractionalBoundsOrderError, InvalidFractionalKeyError

# Форма корректного ключа: цифры base-62, последняя — не «0».
_KEY_FORM = re.compile(r"[0-9A-Za-z]*[1-9A-Za-z]")
_SEED = 20261003
_INSERTIONS = 500


def test_generate_key_between_empty_list_returns_valid_key() -> None:
    """Пустой список: обе границы None → корректный непустой ключ."""
    key = generate_key_between(before=None, after=None)

    assert _KEY_FORM.fullmatch(key)


def test_generate_key_between_after_last_is_greater() -> None:
    """Без верхней границы: ключ больше нижней."""
    key = generate_key_between(before="a1", after=None)

    assert key > "a1"
    assert _KEY_FORM.fullmatch(key)


def test_generate_key_between_before_first_is_smaller() -> None:
    """Без нижней границы: ключ меньше верхней."""
    key = generate_key_between(before=None, after="a1")

    assert key < "a1"
    assert _KEY_FORM.fullmatch(key)


def test_generate_key_between_below_smallest_single_digit() -> None:
    """Ниже «1» есть место: ключ начинается с «0» и на «0» не кончается."""
    key = generate_key_between(before=None, after="1")

    assert key < "1"
    assert _KEY_FORM.fullmatch(key)


@pytest.mark.parametrize(
    ("before", "after"),
    [("a", "b"), ("a", "a1"), ("Z", "a"), ("a0z", "a1"), ("1", "2"), ("az", "b"), ("ay", "az")],
)
def test_generate_key_between_tight_neighbors_returns_key_strictly_between(before: str, after: str) -> None:
    """Соседние ключи (одна цифра разницы, префикс, стык регистров): новый ключ строго между ними."""
    key = generate_key_between(before=before, after=after)

    assert before < key < after
    assert _KEY_FORM.fullmatch(key)


def test_generate_key_between_random_insertions_keep_strict_order() -> None:
    """Сотни вставок в случайные места: список остаётся строго возрастающим, все ключи корректны."""
    # Генератор с сидом — для воспроизводимых позиций вставки, не для криптографии.
    rng = random.Random(_SEED)  # noqa: S311
    keys: list[str] = []
    for _ in range(_INSERTIONS):
        position = rng.randint(0, len(keys))
        before = keys[position - 1] if position > 0 else None
        after = keys[position] if position < len(keys) else None
        keys.insert(position, generate_key_between(before=before, after=after))

    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    assert all(_KEY_FORM.fullmatch(key) for key in keys)


@pytest.mark.parametrize("edge", ["start", "end"])
def test_generate_key_between_repeated_edge_insertions_grow_slowly(edge: str) -> None:
    """Вставки подряд в начало или конец: порядок держится, ключ растёт примерно на символ за 60 вставок."""
    keys = [generate_key_between(before=None, after=None)]
    for _ in range(_INSERTIONS):
        if edge == "end":
            keys.append(generate_key_between(before=keys[-1], after=None))
        else:
            keys.insert(0, generate_key_between(before=None, after=keys[0]))

    assert keys == sorted(keys)
    assert max(len(key) for key in keys) <= _INSERTIONS // 60 + 2


@pytest.mark.parametrize(("before", "after"), [("b", "a"), ("a1", "a1")])
def test_generate_key_between_bounds_not_ascending_raises(before: str, after: str) -> None:
    """before ≥ after → FractionalBoundsOrderError с обеими границами в сообщении."""
    with pytest.raises(FractionalBoundsOrderError) as exc_info:
        generate_key_between(before=before, after=after)

    assert repr(before) in str(exc_info.value)
    assert repr(after) in str(exc_info.value)


@pytest.mark.parametrize("key", ["", "a0", "a-1", "ключ"])
def test_generate_key_between_malformed_key_raises(key: str) -> None:
    """Пустой ключ, ключ на «0» или с чужими символами → InvalidFractionalKeyError с ключом в сообщении."""
    with pytest.raises(InvalidFractionalKeyError) as exc_info:
        generate_key_between(before=key, after=None)

    assert repr(key) in str(exc_info.value)
