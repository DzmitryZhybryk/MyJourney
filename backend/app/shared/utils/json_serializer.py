from typing import Any

import orjson


def serialize_to_json(obj: Any, **kwargs: Any) -> str:
    """
    Сериализация в JSON с поддержкой кириллицы.

    Scenarios:
        - запись логов в JSON: кириллица пишется как есть
    """
    dumps = orjson.dumps
    return dumps(obj, **kwargs).decode("utf-8")
