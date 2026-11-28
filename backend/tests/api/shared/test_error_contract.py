"""Статус каждой категории проверяет unit-тест ``resolve_http_status``; здесь — форма тела ошибки."""

import datetime as dt

from httpx import AsyncClient


async def test_app_error_envelope_has_all_fields(error_contract_client: AsyncClient) -> None:
    """``AppError`` отдаёт полный envelope ``{code, message, details, timestamp}``."""
    response = await error_contract_client.get("/app-error")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["message"]
    assert "details" in body
    assert dt.datetime.fromisoformat(body["timestamp"])


async def test_field_bound_error_carries_details_field(error_contract_client: AsyncClient) -> None:
    """Ошибка, привязанная к полю формы, несёт ``details.field`` с его именем."""
    response = await error_contract_client.get("/field-error")

    assert response.status_code == 400
    assert response.json()["details"] == {"field": "password"}


async def test_validation_error_envelope_lists_fields(error_contract_client: AsyncClient) -> None:
    """422 от FastAPI сворачивается в ``validation_error`` со списком ``details.fields`` (поле и причина)."""
    response = await error_contract_client.post("/validated", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    fields = body["details"]["fields"]
    assert fields
    for field_error in fields:
        assert isinstance(field_error["field"], str)
        assert isinstance(field_error["reason"], str)


async def test_non_app_error_returns_internal_without_leak(error_contract_client: AsyncClient) -> None:
    """Исключение вне ``AppError`` → 500 ``internal`` без сообщения исключения и трейсбека."""
    response = await error_contract_client.get("/unhandled")

    assert response.status_code == 500
    assert response.json() == {"code": "internal", "message": "Внутренняя ошибка сервера"}
    assert "unhandled failure" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
