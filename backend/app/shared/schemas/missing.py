from pydantic.experimental.missing_sentinel import MISSING


def none_if_missing[T](value: T | MISSING) -> T | None:
    """
    Переводит отсутствующее в запросе поле в ``None`` для command, где ``None`` — «не менять».

    Scenarios:
        - частичная правка ресурса: поле, которого нет в теле запроса, не меняется

    Args:
        value: Поле запроса

    Returns:
        Значение поля; ``None``, если его не прислали
    """
    return None if value is MISSING else value
