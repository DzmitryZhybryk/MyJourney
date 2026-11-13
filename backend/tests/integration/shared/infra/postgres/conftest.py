import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def uow_probe_table(_postgres_container: PostgresContainer) -> sa.Table:
    """
    Пробная таблица для тестов ``BaseUnitOfWork``: своя ``MetaData``, в схему приложения не входит.

    Создаётся один раз на сессию синхронным движком, как основная схема в ``integration/conftest.py``.
    В TRUNCATE между тестами не попадает — тесты пишут и ищут строку по своему ``uuid``.
    """
    metadata = sa.MetaData()
    table = sa.Table("uow_probe", metadata, sa.Column("id", sa.Uuid, primary_key=True))
    sync_engine = create_engine(_postgres_container.get_connection_url())
    try:
        metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()

    return table
