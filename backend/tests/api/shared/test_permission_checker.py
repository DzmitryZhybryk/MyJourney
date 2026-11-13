"""
api-тесты ``PermissionChecker`` на маршруте ``/guarded/`` приложения ``guarded_app``.

Токен с правом проходит; без права — 403 ``permission_required``; испорченный claim прав — 401, а не 403;
``user_id`` попадает в строку лога и у отказа по правам.
"""

import datetime as dt
from collections.abc import Callable
from uuid import uuid4

import jwt
from httpx import AsyncClient
from structlog.testing import capture_logs
from structlog.typing import Processor

from app.shared.schemas.base import BFastAPI
from app.shared.settings import settings

type MakeAsyncClient = Callable[[BFastAPI], AsyncClient]


async def test_guarded_route_with_permission_passes(
    guarded_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    mint_access_token: Callable[..., str],
    guarded_permission: str,
) -> None:
    """Право в токене → маршрут отвечает 200 и получает содержимое токена."""
    user_id = uuid4()
    token = mint_access_token(user_id=user_id, permissions=frozenset({guarded_permission, "other.permission"}))

    async with make_async_client(guarded_app) as client:
        response = await client.get("/guarded/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}


async def test_guarded_route_without_permission_is_403_permission_required(
    guarded_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """Валидный токен без нужного права → 403 с кодом permission_required, даже с ролью admin."""
    token = mint_access_token(user_id=uuid4(), role="admin", permissions=frozenset({"other.permission"}))

    async with make_async_client(guarded_app) as client:
        response = await client.get("/guarded/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["code"] == "permission_required"


async def test_guarded_route_without_token_is_401(
    guarded_app: BFastAPI,
    make_async_client: MakeAsyncClient,
) -> None:
    """Без токена отказ — 401 (не знаем, кто это), а не 403."""
    async with make_async_client(guarded_app) as client:
        response = await client.get("/guarded/")

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_guarded_route_with_malformed_permissions_claim_is_401(
    guarded_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    guarded_permission: str,
) -> None:
    """Claim permissions — строка, а не список: ошибка выпуска токена → 401, а не тихий 403."""
    now = dt.datetime.now(tz=dt.UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "admin",
            "plan": "free",
            "email_verified": True,
            "permissions": guarded_permission,
            "iat": int(now.timestamp()),
            "exp": int((now + dt.timedelta(minutes=5)).timestamp()),
        },
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )

    async with make_async_client(guarded_app) as client:
        response = await client.get("/guarded/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_guarded_route_denied_request_logs_user_id(
    guarded_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
    mint_access_token: Callable[..., str],
) -> None:
    """Отказ по правам: в строке лога запроса есть user_id из токена — видно, кто стучался."""
    user_id = uuid4()
    token = mint_access_token(user_id=user_id)
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(guarded_app) as client:
            response = await client.get("/guarded/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    (line,) = [entry for entry in logs if entry["event"] == "http.request"]
    assert line["user_id"] == user_id
    assert line["error_code"] == "permission_required"
