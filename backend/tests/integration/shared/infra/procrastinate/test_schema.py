"""
Integration: ``ensure_procrastinate_schema`` идемпотентна против реального Postgres.

``apply_schema_async()`` не идемпотентен (schema.sql — ``CREATE TABLE`` без
``IF NOT EXISTS``), поэтому шаг миграции гейтит применение по наличию таблицы
``procrastinate_jobs``. Проверяем обе ветки на живой БД: пусто → схема
применяется; повтор на уже мигрированной БД → no-op (не падает на дублирующих
CREATE). Строится тот же ``ProcrastinateApp``, что и в проде, на том же DSN
(``postgres_libpq_dsn``), — покрываем ровно боевой путь.
"""

from procrastinate import PsycopgConnector

from app.shared.infra.procrastinate.component import ProcrastinateApp
from app.shared.infra.procrastinate.schema import ensure_procrastinate_schema
from app.shared.settings import PostgresSettings


async def _procrastinate_jobs_oid(procrastinate_app: ProcrastinateApp) -> object:
    """Возвращает OID таблицы ``procrastinate_jobs`` или ``None``, если её нет."""
    result = await procrastinate_app.connector.execute_query_one_async(
        "SELECT to_regclass('procrastinate_jobs') AS table_oid",
    )
    return result["table_oid"]


async def test_ensure_procrastinate_schema_applies_then_is_idempotent(
    postgres_settings: PostgresSettings,
) -> None:
    """Пустая БД → схема применяется; повторный вызов → no-op (не падает на дублирующих CREATE)."""
    procrastinate_app = ProcrastinateApp(connector=PsycopgConnector(conninfo=postgres_settings.postgres_libpq_dsn))
    await procrastinate_app.open_async()
    try:
        # Прекондиция: свежий контейнер — procrastinate-схемы ещё нет (лоудно ловит контаминацию).
        assert await _procrastinate_jobs_oid(procrastinate_app=procrastinate_app) is None

        # Ветка 1: пусто → схема применяется.
        await ensure_procrastinate_schema(procrastinate_app=procrastinate_app)
        assert await _procrastinate_jobs_oid(procrastinate_app=procrastinate_app) is not None

        # Ветка 2: повтор на мигрированной БД → no-op, дублирующие CREATE не выполняются.
        await ensure_procrastinate_schema(procrastinate_app=procrastinate_app)
        assert await _procrastinate_jobs_oid(procrastinate_app=procrastinate_app) is not None
    finally:
        await procrastinate_app.close_async()
