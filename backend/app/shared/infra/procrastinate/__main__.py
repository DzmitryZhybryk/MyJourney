"""CLI применения procrastinate-схемы: ``python -m app.shared.infra.procrastinate``."""

import asyncio

from app.shared.enums import AppEnvEnum
from app.shared.infra.di.lifecycle import run_components
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.component import ProcrastinateApp, ProcrastinateComponent
from app.shared.infra.procrastinate.schema import ensure_procrastinate_schema
from app.shared.logging import configure_logging
from app.shared.settings import settings


async def main() -> None:
    """
    Применяет procrastinate-схему, если её ещё нет в базе.

    Scenarios:
        - схема очереди фоновых задач при развёртывании, до старта приложения и воркера
    """
    configure_logging(include_debug=settings.ENVIRONMENT in (AppEnvEnum.LOCAL, AppEnvEnum.DEVELOPMENT))

    registry = ComponentRegistry()
    async with run_components(components=[ProcrastinateComponent(settings=settings)], registry=registry):
        await ensure_procrastinate_schema(procrastinate_app=registry.get(ProcrastinateApp))


if __name__ == "__main__":
    asyncio.run(main())
