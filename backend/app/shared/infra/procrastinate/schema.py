"""Применение procrastinate-схемы — шаг миграции, а не старта worker'а или API."""

import procrastinate

from app.shared.infra.procrastinate.component import ProcrastinateApp
from app.shared.logging import get_logger

logger = get_logger(__name__)


async def ensure_procrastinate_schema(*, procrastinate_app: ProcrastinateApp) -> None:
    """
    Применяет procrastinate-схему, если её ещё нет.

    ``apply_schema_async()`` не идемпотентен: schema.sql использует
    ``CREATE TABLE`` без ``IF NOT EXISTS``, повторный вызов на уже
    мигрированной БД упадёт на дублирующих CREATE TABLE. Проверяем
    наличие ключевой таблицы ``procrastinate_jobs`` через ``to_regclass``
    и применяем схему только если её нет. Версию схемы проверка не сверяет.

    Scenarios:
        - схема очереди фоновых задач при развёртывании, до старта приложения и воркера

    Args:
        procrastinate_app: Открытый ``ProcrastinateApp`` (после ``open_async``)
    """
    result = await procrastinate_app.connector.execute_query_one_async(
        "SELECT to_regclass('procrastinate_jobs') AS table_oid",
    )
    if result["table_oid"] is None:
        await procrastinate_app.schema_manager.apply_schema_async()
        logger.info("procrastinate.schema.applied", procrastinate_version=procrastinate.__version__)
    else:
        logger.info("procrastinate.schema.already_applied", procrastinate_version=procrastinate.__version__)
