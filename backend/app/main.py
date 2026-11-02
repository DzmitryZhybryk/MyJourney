from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

from fastapi.routing import APIRoute

from app.auth.presentation.routes import auth_router
from app.blueprints import TASK_BLUEPRINTS
from app.geo.presentation.routes import geo_router
from app.health.presentation.routes import health_router
from app.journeys.presentation.routes import journey_router
from app.media.infra.component import MediaStorageComponent
from app.shared.enums import AppEnvEnum
from app.shared.exceptions.handlers import register_exception_handlers
from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.lifecycle import run_components
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email.component import ResendComponent
from app.shared.infra.postgres.component import SqlAlchemyComponent
from app.shared.infra.procrastinate.bus_component import TaskBusComponent
from app.shared.infra.procrastinate.component import ProcrastinateComponent
from app.shared.infra.telemetry.tracing import get_api_telemetry_config
from app.shared.logging import configure_logging, get_logger
from app.shared.logging.middleware import HTTPLoggingMiddleware
from app.shared.schemas.base import BFastAPI
from app.shared.settings import settings
from app.shared.types import DictStrAny
from app.users.presentation.routes import users_router

logger = get_logger(__name__)


def route_operation_id(route: APIRoute) -> str:
    """
    Возвращает operationId маршрута — имя функции-обработчика.

    Дефолт FastAPI склеивает имя, путь и метод (``login_v1_auth_login__post``), из чего
    кодогенератор фронтового SDK делает нечитаемые имена методов. Уникальность имён
    проверяет ``tests/api/test_openapi_schema.py``.

    Scenarios:
        - сборка OpenAPI-документа: имена методов в сгенерированном клиенте фронта

    Args:
        route: Маршрут FastAPI

    Returns:
        Идентификатор операции для OpenAPI
    """
    return route.name


def create_default_app(
    *,
    components: Sequence[BaseComponent] | None = None,
    **kwargs: Any,
) -> BFastAPI:
    """
    Создает BFastAPI приложение с инициализированным registry и lifecycle events.

    Scenarios:
        - запуск API-процесса

    Args:
        components: Список компонентов для регистрации
        **kwargs: Дополнительные аргументы для FastAPI

    Returns:
        BFastAPI приложение с инициализированным registry
    """
    components_list = components or []
    registry = ComponentRegistry()

    @asynccontextmanager
    async def lifespan(_app: BFastAPI) -> AsyncGenerator[None]:
        """
        Lifecycle events для компонентов.

        Scenarios:
            - старт и остановка API-процесса: подъём и закрытие компонентов
        """
        async with run_components(components=components_list, registry=registry):
            logger.info(
                "api.started",
                service_name=_app.title,
                version=_app.version,
            )
            yield

    app = BFastAPI(lifespan=lifespan, **kwargs)
    app.components = components_list
    app.registry = registry

    return app


def create_app() -> BFastAPI:
    """
    Создает и настраивает FastAPI приложение.

    Scenarios:
        - запуск API-процесса: в Docker-стеках dev, e2e и prod и локально
    """
    configure_logging(include_debug=settings.ENVIRONMENT in (AppEnvEnum.LOCAL, AppEnvEnum.DEVELOPMENT))

    # В production не публикуем интерактивную документацию и OpenAPI-схему наружу:
    # это внутренняя поверхность API, её не должно быть видно на публичном домене.
    docs_kwargs: DictStrAny = {}
    if settings.ENVIRONMENT is AppEnvEnum.PRODUCTION:
        docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

    app = create_default_app(
        title="MyJourney",
        version=version("MyJourney"),
        description="Personal travel atlas: journeys, cities and routes on a globe",
        generate_unique_id_function=route_operation_id,
        telemetry=get_api_telemetry_config(),
        components=[
            SqlAlchemyComponent(settings=settings),
            ResendComponent(settings=settings),
            MediaStorageComponent(settings=settings),
            ProcrastinateComponent(settings=settings, blueprints=TASK_BLUEPRINTS),
            TaskBusComponent(),
        ],
        **docs_kwargs,
    )

    app.add_middleware(HTTPLoggingMiddleware)

    register_exception_handlers(app)

    # Операционный эндпоинт вне версионированного контракта (/v1): путь стабилен для
    # docker healthcheck и reverse-proxy независимо от версии API.
    app.include_router(health_router)

    app.include_router(auth_router, prefix="/v1/auth", tags=["auth"])
    app.include_router(geo_router, prefix="/v1/geo", tags=["geo"])
    app.include_router(journey_router, prefix="/v1/journeys", tags=["journeys"])
    app.include_router(users_router, prefix="/v1/users", tags=["users"])

    return app
