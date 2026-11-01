"""
Дробные ключи порядка (fractional indexing).

Ключ — строка из цифр base-62, порядок ключей — побайтное сравнение строк. Между любыми двумя
ключами всегда найдётся третий, поэтому перенос элемента списка меняет ключ только у него самого,
соседей не трогает. В базе колонке с такими ключами нужна коллация ``"C"``: сравнение по правилам
языка (``a < B``) разошлось бы с побайтным (``B < a``).

Ключ не заканчивается на ``0`` — иначе между ``a`` и ``a0`` не было бы места.
"""

import re
import string

from app.shared.fractional_index.exceptions import FractionalBoundsOrderError, InvalidFractionalKeyError

# Цифры по возрастанию кодов ASCII: побайтный порядок строк совпадает с порядком цифр.
_DIGITS = string.digits + string.ascii_uppercase + string.ascii_lowercase
_BASE = len(_DIGITS)
_KEY_PATTERN = re.compile(r"[0-9A-Za-z]*[1-9A-Za-z]")


def generate_key_between(*, before: str | None, after: str | None) -> str:
    """
    Возвращает ключ строго между ``before`` и ``after``.

    ``None`` вместо границы означает край списка: ``before=None`` — ключ меньше ``after``,
    ``after=None`` — больше ``before``, обе ``None`` — первый ключ пустого списка. Ключ у края
    списка растёт медленно — на символ примерно за каждые 60 вставок подряд в начало или конец.

    Scenarios:
        - любой список с ручным порядком: новая строка в конце области и перенос строки между соседями

    Args:
        before: Ключ, после которого встаёт новый, или ``None``
        after: Ключ, перед которым встаёт новый, или ``None``

    Returns:
        Новый ключ

    Raises:
        InvalidFractionalKeyError: ключ некорректен
        FractionalBoundsOrderError: ``before`` не меньше ``after``
    """
    for key in (before, after):
        if key is not None and not _KEY_PATTERN.fullmatch(key):
            raise InvalidFractionalKeyError(key=key)

    if before is not None and after is not None and before >= after:
        raise FractionalBoundsOrderError(before=before, after=after)

    return _midpoint(lower=before or "", upper=after)


def _midpoint(*, lower: str, upper: str | None) -> str:
    """
    Строит ключ между ``lower`` и ``upper`` (``upper=None`` — без верхней границы).

    Общий префикс границ переносится в ответ как есть, дальше решает первая различающаяся цифра.
    ``lower`` короче нужного дополняется нулями.

    Scenarios:
        - любой список с ручным порядком: ключ между двумя соседями

    Args:
        lower: Нижняя граница, пустая строка — без нижней границы
        upper: Верхняя граница или ``None``

    Returns:
        Ключ строго между границами
    """
    if upper is not None:
        prefix_len = 0
        while prefix_len < len(upper) and _digit_at(key=lower, index=prefix_len) == upper[prefix_len]:
            prefix_len += 1

        if prefix_len:
            return upper[:prefix_len] + _midpoint(lower=lower[prefix_len:], upper=upper[prefix_len:])

    lower_digit = _DIGITS.index(lower[0]) if lower else 0
    upper_digit = _DIGITS.index(upper[0]) if upper is not None else _BASE

    # У края списка — наименьший шаг от соседа, а не середина: ключ удлиняется реже.
    if upper is None and lower_digit + 1 < _BASE:
        return _DIGITS[lower_digit + 1]

    if not lower and upper is not None:
        if upper_digit > 1:
            return _DIGITS[upper_digit - 1]

        # Ниже «1» — только «0…»; ключ на 0 кончаться не может, берём самый большой хвост.
        if len(upper) == 1:
            return _DIGITS[0] + _DIGITS[-1]

    if upper_digit - lower_digit > 1:
        return _DIGITS[(lower_digit + upper_digit) // 2]

    # Соседние цифры: если у верхней границы есть продолжение, её первая цифра уже между ними.
    if upper is not None and len(upper) > 1:
        return upper[0]

    return _DIGITS[lower_digit] + _midpoint(lower=lower[1:], upper=None)


def _digit_at(*, key: str, index: int) -> str:
    """
    Цифра ключа в позиции ``index``; за концом ключа — ``0``.

    Scenarios:
        - любой список с ручным порядком: ключ между двумя соседями
    """
    return key[index] if index < len(key) else _DIGITS[0]
