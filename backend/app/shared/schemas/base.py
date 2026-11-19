from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.shared.exceptions.openapi import rewrite_validation_responses
from app.shared.types import DictStrAny

if TYPE_CHECKING:
    from app.shared.infra.di.base import BaseComponent
    from app.shared.infra.di.registry import ComponentRegistry


class BFastAPI(FastAPI):
    components: Sequence[BaseComponent]
    registry: ComponentRegistry

    def openapi(self) -> DictStrAny:
        """
        Возвращает OpenAPI-документ, приведённый к фактическому контракту ошибок.

        Scenarios:
            - сборка OpenAPI-документа: ``/docs``, снапшот контракта и генерация клиента фронта

        Returns:
            OpenAPI-схема приложения
        """
        schema = super().openapi()
        rewrite_validation_responses(schema)

        return schema


class CamelModel(BaseModel):
    """
    Базовая модель HTTP-границы: поля на проводе сериализуются в camelCase.

    Внутри Python поля остаются snake_case (PEP 8), а наружу (JSON request/response)
    уходят/принимаются как camelCase через ``alias_generator=to_camel``. От неё
    наследуются ВСЕ presentation ``*Request``/``*Response`` — это единственное место,
    где задаётся casing провода. Application DTO и domain остаются snake_case.

    ``validate_by_name`` + ``validate_by_alias`` оба ``True``: модель принимает на входе
    и camelCase-алиас (основной контракт), и snake-имя поля (страховка переходного
    периода). FastAPI сериализует ответы по алиасам (``response_model_by_alias`` = True
    по умолчанию), поэтому наружу всегда уходит camelCase.
    """

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)
