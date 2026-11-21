from typing import Any

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from app.shared.types import OptionalDict


class PydanticJSONB[T: BaseModel](TypeDecorator[T]):
    """
    Колонка JSONB, типизированная pydantic-моделью: на запись — ``model_dump``, на чтение — ``model_validate``.

    ``none_as_null=True`` пишет Python ``None`` как SQL ``NULL``, а не JSON ``null``. ``__eq__``/``__hash__``
    включают класс модели в ключ statement cache SQLAlchemy: без них две колонки с разными моделями
    получили бы один ключ, и результат одной разбирался бы моделью другой.
    """

    impl = JSONB(none_as_null=True)
    cache_ok = True

    def __init__(self, model: type[T]) -> None:
        super().__init__()
        self._model = model

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PydanticJSONB) and self._model is other._model

    def __hash__(self) -> int:
        return hash((self.__class__, self._model))

    def process_bind_param(self, value: T | None, dialect: Any) -> OptionalDict:
        if value is None:
            return None

        return value.model_dump(mode="json")

    def process_result_value(self, value: OptionalDict, dialect: Any) -> T | None:
        if value is None:
            return None

        return self._model.model_validate(value)
