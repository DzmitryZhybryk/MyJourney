"""
api-тесты единого контракта ошибок (через auth-роуты).

Пиннят форму ``ErrorResponse``-envelope, общую для всех ошибок: ``AppError`` несут
``{code, message, details, timestamp}``; field-bound кладут ``details.field``; 422 от
FastAPI заворачивается в ``code="validation_error"`` с ``details.fields[]``; исключение
вне ``AppError`` даёт ``{code: "internal"}`` без утечки внутренних деталей.

Категории, недостижимые auth-роутами (403 PERMISSION_DENIED, 422 UNPROCESSABLE от ``AppError``),
покрыты юнит-тестом ``resolve_http_status`` (``tests/unit/shared/exceptions/test_mappings.py``).
"""

import datetime as dt

from httpx import AsyncClient

from tests.fakes import FakeAuthUnitOfWork


async def test_app_error_envelope_has_all_fields(client: AsyncClient) -> None:
    """AppError отдаёт полный envelope {code, message, details, timestamp}."""
    response = await client.post("/v1/auth/login/", json={"login": "ghost@example.com", "password": "whatever123"})

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "auth.invalid_credentials"
    assert body["message"]
    assert "details" in body
    assert dt.datetime.fromisoformat(body["timestamp"])


async def test_field_bound_error_carries_details_field(client: AsyncClient) -> None:
    """Field-bound AppError несёт details.field с именем поля формы."""
    response = await client.post(
        "/v1/auth/register/",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "terms_accepted": False,
            "marketing_emails_consent": False,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "auth.terms_not_accepted"
    assert body["details"] == {"field": "terms_accepted"}


async def test_validation_error_envelope_lists_fields(client: AsyncClient) -> None:
    """422 от FastAPI сворачивается в code=validation_error с details.fields[] (field + reason)."""
    response = await client.post("/v1/auth/register/", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    fields = body["details"]["fields"]
    assert isinstance(fields, list)
    assert fields
    for field_error in fields:
        assert isinstance(field_error["field"], str)
        assert isinstance(field_error["reason"], str)


async def test_non_app_error_returns_internal_without_leak(
    client: AsyncClient,
    fake_uow: FakeAuthUnitOfWork,
) -> None:
    """Исключение вне AppError → 500 {code: internal} без утечки сообщения/трейсбека."""
    fake_uow.commit_mock.side_effect = RuntimeError("secret internal boom")

    response = await client.post(
        "/v1/auth/register/",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "terms_accepted": True,
            "marketing_emails_consent": False,
        },
    )

    assert response.status_code == 500
    assert response.json() == {"code": "internal", "message": "Внутренняя ошибка сервера"}
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
