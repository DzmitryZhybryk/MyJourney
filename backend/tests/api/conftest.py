import datetime as dt
from collections.abc import AsyncIterator, Callable
from typing import Any, Final
from uuid import UUID

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient, Response

from app.auth.application.services.token_issuer import TokenIssuer
from app.auth.domain.entities import UserCredentialsEntity
from app.main import create_app, create_default_app
from app.shared.exceptions.handlers import register_exception_handlers
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher
from app.shared.infra.jwt import AccessTokenClaims, get_jwt_service
from app.shared.schemas.base import BFastAPI
from app.shared.types import DictStrAny
from tests.builders import make_refresh_token

_BASE_URL: Final[str] = "http://testserver"


@pytest.fixture
def api_app() -> BFastAPI:
    app = create_default_app()
    register_exception_handlers(app)
    return app


@pytest.fixture
def production_app() -> BFastAPI:
    """Боевое приложение из ``create_app`` — со всеми роутерами, middleware и телеметрией; компоненты не стартуют."""
    return create_app()


@pytest.fixture
def openapi_schema(production_app: BFastAPI) -> DictStrAny:
    """Схема боевого приложения — со всеми роутерами, тегами и версией (в отличие от ``api_app``)."""
    return production_app.openapi()


@pytest.fixture
def app(
    api_app: BFastAPI,
    router: APIRouter,
    router_prefix: str,
    dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
) -> BFastAPI:
    """
    Собранное ASGI-приложение под тест.

    Механизм домен-агностичен: смонтировать ``router`` под ``router_prefix`` и применить
    карту ``dependency_overrides``. Сами данные (роутер, префикс, что чем подменять) даёт
    доменный conftest — поэтому второй домен переиспользует эту фикстуру как есть, отдав
    лишь три свои data-фикстуры, а не копируя ``include_router`` + цикл override'ов.
    """
    api_app.include_router(router, prefix=router_prefix)
    api_app.dependency_overrides.update(dependency_overrides)
    return api_app


@pytest.fixture
def make_async_client() -> Callable[[BFastAPI], AsyncClient]:
    """
    ``raise_app_exceptions=False``: Starlette после 500-ответа поднимает исходное исключение повторно, и тест
    получил бы его вместо тела ответа.
    """

    def _factory(app: BFastAPI) -> AsyncClient:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        return AsyncClient(transport=transport, base_url=_BASE_URL)

    return _factory


@pytest.fixture
async def client(app: BFastAPI, make_async_client: Callable[[BFastAPI], AsyncClient]) -> AsyncIterator[AsyncClient]:
    """
    httpx-клиент поверх собранного ``app``.

    Тело домен-агностично — клиент лишь оборачивает ``make_async_client``. Конкретный
    ``app`` (с роутером и override'ами) предоставляет доменный conftest: ``client`` зависит
    от абстрактной фикстуры ``app``, которую pytest резолвит вниз по дереву теста
    (шаблонная фикстура). Любой будущий домен, объявив свою ``app``, получает ``client``
    даром.
    """
    async with make_async_client(app) as async_client:
        yield async_client


@pytest.fixture
def find_set_cookie() -> Callable[..., str | None]:
    """Сырой ``Set-Cookie`` по имени: httpx-jar не хранит ``Secure``-cookie поверх ``http://`` и скрыл бы атрибуты."""

    def _find(*, response: Response, name: str) -> str | None:
        for header in response.headers.get_list("set-cookie"):
            if header.startswith(f"{name}="):
                return header

        return None

    return _find


@pytest.fixture
def past() -> dt.datetime:
    """Фиксированная дата в прошлом для просроченных/отозванных сущностей в api-сценариях."""
    return dt.datetime(2000, 1, 1, tzinfo=dt.UTC)


@pytest.fixture
def mint_access_token() -> Callable[..., str]:
    """
    Фабрика валидных access-токенов через реальный ``get_jwt_service()``.

    Токен подписывается тем же секретом из ``settings``, которым приложение его и декодит,
    поэтому Bearer проходит настоящий ``current_user_id_dependency`` без override'а.
    """
    jwt_service = get_jwt_service()

    def _mint(
        *,
        user_id: UUID,
        role: str = "user",
        plan: str = "free",
        permissions: frozenset[str] = frozenset(),
        email_verified: bool = False,
    ) -> str:
        return jwt_service.create_access_token(
            AccessTokenClaims(
                user_id=user_id,
                role=role,
                plan=plan,
                permissions=permissions,
                email_verified=email_verified,
            ),
        )

    return _mint


@pytest.fixture
def issue_access_token(deterministic_hasher: Sha256DeterministicHasher) -> Callable[[UserCredentialsEntity], str]:
    """
    Access-токен, выпущенный настоящим ``TokenIssuer``: права раскрываются из роли и тарифа, как при входе.

    В отличие от ``mint_access_token`` права здесь не задаются руками, поэтому тест маршрута, закрытого
    правом, ловит расхождение имени права в маршруте и в карте ролей.
    """
    token_issuer = TokenIssuer(
        deterministic_hasher=deterministic_hasher,
        access_token_issuer=get_jwt_service(),
        refresh_token_ttl_days=30,
    )

    def _issue(user_credentials_entity: UserCredentialsEntity) -> str:
        token_pair = token_issuer.build_token_pair(
            user_credentials_entity=user_credentials_entity,
            refresh_secret="refresh-secret",
            refresh_token_entity=make_refresh_token(user_id=user_credentials_entity.user_id),
        )
        return token_pair.access_token.get_secret_value()

    return _issue
