"""CLI начального конфига media: ``python -m app.media.scripts.seed_config``."""

import asyncio
from pathlib import Path
from typing import Final

from app.media.application.ports.media_config_repository import MediaConfigSnapshot
from app.media.application.schemas.commands import SeedMediaConfigCommand
from app.media.application.services.media_config import MediaConfigService
from app.media.infra.uow import MediaUnitOfWork
from app.shared.enums import AppEnvEnum
from app.shared.infra.di.lifecycle import run_components
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.postgres.component import SessionMaker, SqlAlchemyComponent
from app.shared.logging import configure_logging
from app.shared.settings import settings

_DEFAULTS_PATH: Final[Path] = Path(__file__).with_name("config_defaults.json")


async def main() -> None:
    """
    Записывает начальный конфиг media из ``config_defaults.json``, если конфига ещё нет.

    Scenarios:
        - начальное значение конфига при развёртывании, до старта приложения
    """
    configure_logging(include_debug=settings.ENVIRONMENT in (AppEnvEnum.LOCAL, AppEnvEnum.DEVELOPMENT))
    snapshot = MediaConfigSnapshot.model_validate_json(_DEFAULTS_PATH.read_text(encoding="utf-8"))

    registry = ComponentRegistry()
    async with (
        run_components(components=[SqlAlchemyComponent(settings=settings)], registry=registry),
        registry.get(SessionMaker)() as session,
    ):
        media_config_service = MediaConfigService(uow=MediaUnitOfWork(session=session))
        await media_config_service.seed_media_config(command=SeedMediaConfigCommand(snapshot=snapshot))


if __name__ == "__main__":
    asyncio.run(main())
