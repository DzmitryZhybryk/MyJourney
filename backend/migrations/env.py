import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.runtime.environment import NameFilterParentNames, NameFilterType
from alembic.runtime.plugins import Plugin
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Импорт базового класса моделей и явная загрузка модулей с моделями,
# чтобы все таблицы регистрировались в BaseDBModel.metadata для autogenerate.
from app.auth.infra import models as _auth_models  # noqa: F401
from app.geo.infra import models as _geo_models  # noqa: F401
from app.journeys.infra import models as _journeys_models  # noqa: F401
from app.shared.models import BaseDBModel
from app.shared.settings import settings
from app.users.infra import models as _users_models  # noqa: F401
from migrations.plugins import opclass_compare

Plugin.setup_plugin_from_module(opclass_compare, opclass_compare.PLUGIN_NAME)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

target_metadata = BaseDBModel.metadata

_PROCRASTINATE_TABLE_PREFIX = "procrastinate_"


def include_name(name: str | None, type_: NameFilterType, parent_names: NameFilterParentNames) -> bool:
    """
    Исключает таблицы procrastinate из сравнения, которое делает ``alembic revision --autogenerate``.

    Autogenerate сверяет таблицы в базе с ``BaseDBModel.metadata``. Таблиц procrastinate
    (``procrastinate_jobs`` и соседних) в metadata нет: это не наши модели, их создаёт сама
    библиотека. Без фильтра каждая новая ревизия предлагала бы их удалить, и лишний
    ``drop_table`` легко пропустить при ревью миграции.

    Схему procrastinate alembic не ведёт: её применяет отдельная команда
    ``python -m app.shared.infra.procrastinate`` в шаге миграции, сразу после ``alembic upgrade head``.
    В alembic её не кладём, потому что у procrastinate нет SQL для удаления схемы, и
    ``alembic downgrade`` такой ревизии было бы нечем выполнить.

    Args:
        name: Имя объекта
        type_: Тип объекта (``table``, ``column``, ``index``, …)
        parent_names: Имена родительских объектов (сигнатура alembic-хука)

    Returns:
        ``False`` для таблиц procrastinate, иначе ``True``
    """
    return not (type_ == "table" and name is not None and name.startswith(_PROCRASTINATE_TABLE_PREFIX))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_name=include_name,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        autogenerate_plugins=["alembic.autogenerate.*", opclass_compare.PLUGIN_NAME],
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
