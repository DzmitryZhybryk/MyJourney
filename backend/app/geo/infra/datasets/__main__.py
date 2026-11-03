"""CLI загрузки датасетов из ``manifest.toml``: ``python -m app.geo.infra.datasets``."""

from typing import Final

import httpx

from app.geo.infra.datasets.loader import load_datasets
from app.geo.infra.datasets.manifest import read_manifest
from app.shared.enums import AppEnvEnum
from app.shared.logging import configure_logging
from app.shared.settings import settings

_DOWNLOAD_TIMEOUT_SECONDS: Final[float] = 60.0


def main() -> None:
    """
    Загружает недостающие датасеты из манифеста в базу.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    configure_logging(include_debug=settings.ENVIRONMENT in (AppEnvEnum.LOCAL, AppEnvEnum.DEVELOPMENT))
    with httpx.Client(follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as http_client:
        load_datasets(
            datasets=read_manifest(),
            cache_dir=settings.GEO_DATASETS_CACHE_DIR,
            dsn=settings.postgres_libpq_dsn,
            http_client=http_client,
        )


if __name__ == "__main__":
    main()
