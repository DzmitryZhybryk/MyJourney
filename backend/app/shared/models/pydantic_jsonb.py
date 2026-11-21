from typing import Any

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from app.shared.types import OptionalDict


class PydanticJSONB[T: BaseModel](TypeDecorator[T]):
    """
    Колонка JSONB, типизированная pydantic-моделью: на запись — ``model_dump``, на чтение — ``model_validate``.

    ``none_as_null=True`` пишет Python ``None`` как SQL ``NULL``, а не JSON ``null``. Атрибут ``model``
    назван как аргумент ``__init__`` намеренно: только такие атрибуты SQLAlchemy кладёт в ключ statement
    cache. С приватным именем один и тот же SQL, прочитанный разными моделями, получил бы один ключ,
    и результат разбирался бы моделью первого запроса.
    """

    impl = JSONB(none_as_null=True)
    cache_ok = True

    def __init__(self, model: type[T]) -> None:
        super().__init__()
        self.model = model

    def process_bind_param(self, value: T | None, dialect: Any) -> OptionalDict:
        if value is None:
            return None

        return value.model_dump(mode="json")

    def process_result_value(self, value: OptionalDict, dialect: Any) -> T | None:
        if value is None:
            return None

        return self.model.model_validate(value)
