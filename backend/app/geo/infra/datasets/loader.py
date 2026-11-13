import gzip
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx
import psycopg
from psycopg import sql

from app.geo.infra.datasets.cache import ensure_cached
from app.geo.infra.datasets.manifest import DatasetFormatEnum, DatasetSpec
from app.geo.infra.datasets.rows import CITY_TABLE_COLUMNS, PLACE_TABLE_COLUMNS, iter_city_rows, iter_place_rows
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _TableLoad:
    """Как файл датасета одного формата ложится в свою таблицу: SQL загрузки и разбор строк файла."""

    create_staging: sql.Composed
    copy: sql.Composed
    upsert: sql.Composed
    iter_rows: Callable[..., Iterator[tuple[object, ...]]]


def _table_load(
    *,
    table: str,
    columns: tuple[str, ...],
    iter_rows: Callable[..., Iterator[tuple[object, ...]]],
) -> _TableLoad:
    """
    Собирает SQL загрузки в ``table`` через временную staging-таблицу той же структуры.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        table: Таблица газеттира
        columns: Колонки, которые заполняет загрузчик, — в порядке значений из ``iter_rows``
        iter_rows: Разбор строк файла этого формата

    Returns:
        SQL загрузки и разбор строк для файла этого формата
    """
    table_name = sql.Identifier(table)
    staging_name = sql.Identifier(f"{table}_staging")
    column_names = sql.SQL(", ").join(map(sql.Identifier, columns))
    return _TableLoad(
        create_staging=sql.SQL("CREATE TEMP TABLE {staging} (LIKE {table}) ON COMMIT DROP").format(
            staging=staging_name,
            table=table_name,
        ),
        copy=sql.SQL("COPY {staging} ({columns}) FROM STDIN").format(staging=staging_name, columns=column_names),
        upsert=sql.SQL(
            "INSERT INTO {table} ({columns}) SELECT {columns} FROM {staging} "
            "ON CONFLICT (id) DO UPDATE SET {assignments}",
        ).format(
            table=table_name,
            columns=column_names,
            staging=staging_name,
            assignments=sql.SQL(", ").join(
                sql.SQL("{column} = EXCLUDED.{column}").format(column=sql.Identifier(column))
                for column in columns
                if column != "id"
            ),
        ),
        iter_rows=iter_rows,
    )


_TABLE_LOADS: Final[Mapping[DatasetFormatEnum, _TableLoad]] = {
    DatasetFormatEnum.CITIES: _table_load(table="geo_cities", columns=CITY_TABLE_COLUMNS, iter_rows=iter_city_rows),
    DatasetFormatEnum.PLACES: _table_load(table="geo_places", columns=PLACE_TABLE_COLUMNS, iter_rows=iter_place_rows),
}


def load_datasets(
    *,
    datasets: Iterable[DatasetSpec],
    cache_dir: Path,
    dsn: str,
    http_client: httpx.Client,
) -> None:
    """
    Загружает датасеты, которых ещё нет в базе.

    Датасет с той же версией и sha256 в ``geo_dataset_loads`` пропускается. Остальные пишутся
    upsert'ом в таблицу своего формата, в одной транзакции вместе с записью о загрузке. Объекты
    газеттира не удаляются.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        datasets: Датасеты из манифеста
        cache_dir: Папка кеша файлов
        dsn: libpq DSN базы
        http_client: HTTP-клиент, следующий редиректам
    """
    with psycopg.connect(dsn, autocommit=True) as connection:
        for spec in datasets:
            if _is_loaded(connection=connection, spec=spec):
                logger.info("geo.dataset.skipped", dataset=spec.name, version=spec.version)
                continue

            path = ensure_cached(spec=spec, cache_dir=cache_dir, http_client=http_client)
            with connection.transaction():
                rows_count = _load_file(connection=connection, path=path, table_load=_TABLE_LOADS[spec.format])
                _record_load(connection=connection, spec=spec)

            logger.info("geo.dataset.loaded", dataset=spec.name, version=spec.version, rows=rows_count)


def _is_loaded(*, connection: psycopg.Connection, spec: DatasetSpec) -> bool:
    """
    Проверяет, загружена ли уже эта версия датасета.

    Scenarios:
        - загрузка газеттира в базу: уже загруженная версия пропускается
    """
    cursor = connection.execute(
        "SELECT 1 FROM geo_dataset_loads WHERE name = %s AND version = %s AND sha256 = %s",
        (spec.name, spec.version, spec.sha256),
    )
    return cursor.fetchone() is not None


def _load_file(*, connection: psycopg.Connection, path: Path, table_load: _TableLoad) -> int:
    """
    Копирует файл во временную staging-таблицу и переносит её upsert'ом в таблицу формата.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        connection: Соединение с открытой транзакцией
        path: Проверенный файл датасета
        table_load: SQL загрузки и разбор строк для формата датасета

    Returns:
        Количество строк в файле
    """
    connection.execute(table_load.create_staging)

    rows_count = 0
    with (
        gzip.open(path, "rt", encoding="utf-8", newline="") as dataset_file,
        connection.cursor() as cursor,
        cursor.copy(table_load.copy) as copy,
    ):
        for row in table_load.iter_rows(lines=dataset_file):
            copy.write_row(row)
            rows_count += 1

    connection.execute(table_load.upsert)
    return rows_count


def _record_load(*, connection: psycopg.Connection, spec: DatasetSpec) -> None:
    """
    Записывает загрузку датасета в журнал.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    connection.execute(
        """
        INSERT INTO geo_dataset_loads (name, version, sha256, loaded_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (name) DO UPDATE
        SET version = EXCLUDED.version, sha256 = EXCLUDED.sha256, loaded_at = EXCLUDED.loaded_at
        """,
        (spec.name, spec.version, spec.sha256),
    )
