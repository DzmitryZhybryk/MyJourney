"""
Контракт публикуемого набора ``transport_type``.

Пиннит значения ``TransportTypeEnum`` ровно так, как они уходят клиенту в OpenAPI-схеме тела
``POST /v1/journeys/``. Набор закрытый (среда передвижения, не вид транспорта) и меняется почти
никогда. Фронт получает его сгенерированным типом из этой схемы; новое значение роняет тест здесь,
напоминая, что фронту нужны его иконка, визуал маршрута и подписи.
"""

from app.journeys.presentation.routes import journey_router
from app.shared.schemas.base import BFastAPI

_EXPECTED_TRANSPORT_TYPES = {"land", "air", "water"}


def test_openapi_publishes_expected_transport_types(api_app: BFastAPI) -> None:
    """OpenAPI тела POST /v1/journeys/ публикует ровно {land, air, water} для transport_type."""
    api_app.include_router(journey_router, prefix="/v1/journeys")

    schema = api_app.openapi()

    transport_enum = set(schema["components"]["schemas"]["TransportTypeEnum"]["enum"])
    assert transport_enum == _EXPECTED_TRANSPORT_TYPES
