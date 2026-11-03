"""Приведение OpenAPI-документа к фактическому контракту ошибок."""

from typing import Final

from app.shared.types import DictStrAny

_ERROR_RESPONSE_REF: Final[str] = "#/components/schemas/ErrorResponse"
_VALIDATION_DESCRIPTION: Final[str] = "Ошибка валидации запроса"
_FASTAPI_VALIDATION_SCHEMAS: Final[tuple[str, ...]] = ("HTTPValidationError", "ValidationError")


def rewrite_validation_responses(schema: DictStrAny) -> None:
    """
    Переписывает 422-ответы документа на ``ErrorResponse``.

    FastAPI проставляет роутам с телом или параметрами свой ``HTTPValidationError``, но 422
    перехватывает ``validation_exception_handler`` и заворачивает в общий envelope. Без правки
    схема обещает клиенту форму, которой не существует, а кодогенератор SDK делает по ней тип.

    Scenarios:
        - сборка OpenAPI-документа: ``/docs``, снапшот контракта и генерация клиента фронта

    Args:
        schema: OpenAPI-документ; изменяется на месте
    """
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            validation_response = operation.get("responses", {}).get("422")
            if validation_response is None:
                continue

            validation_response["description"] = _VALIDATION_DESCRIPTION
            validation_response["content"] = {"application/json": {"schema": {"$ref": _ERROR_RESPONSE_REF}}}

    component_schemas = schema.get("components", {}).get("schemas", {})
    for schema_name in _FASTAPI_VALIDATION_SCHEMAS:
        component_schemas.pop(schema_name, None)
