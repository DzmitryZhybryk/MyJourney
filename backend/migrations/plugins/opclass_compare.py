"""
Autogenerate-плагин: сравнивает классы операторов индексов PostgreSQL.

Зачем нужен
-----------
У префиксных индексов ``geo_cities`` (``lower(name_en) text_pattern_ops``) от класса оператора
зависит, пойдёт ли ``LIKE 'abc%'`` по индексу. Alembic этот класс не сравнивает: его PostgreSQL-
сравнение индексов учитывает только выражение и ``nulls_not_distinct``, а ``postgresql_ops``
игнорирует. Поэтому смена ``text_pattern_ops`` на другой класс — в модели или прямо в базе —
оставалась незамеченной: ``alembic check`` был зелёным, а ``revision --autogenerate`` не создавал
миграцию.

Что делает
----------
Плагин читает фактические классы операторов из ``pg_index`` / ``pg_opclass`` (по позициям ключа
индекса) и сравнивает их с тем, что объявлено в модели через ``postgresql_ops``. Класс, который в
модели не указан, считается классом по умолчанию для типа. Расхождение оформляется так же, как
Alembic оформляет изменённый индекс: ``drop_index`` + ``create_index``. В ``downgrade`` индекс
возвращается с теми классами, что были в базе. Если Alembic уже пересоздаёт индекс по другой
причине (например, изменилось выражение), второй раз он не добавляется.

Условия работы
--------------
Индекс в модели должен быть объявлен так, чтобы класс можно было привязать к ключу: выражение
с меткой и ``postgresql_ops`` по этой метке::

    Index(
        "ix_name_prefix",
        func.lower(Model.name).label("name_lower"),
        postgresql_ops={"name_lower": "text_pattern_ops"},
    )

Если положить класс внутрь ``text("lower(name) text_pattern_ops")``, Alembic не сможет разобрать
выражение, выдаст ``UserWarning`` и пропустит индекс, а плагин не сможет привязать класс к ключу
и сочтёт его не заданным (то есть «по умолчанию») — такая запись не поддерживается.
Подключение — в ``migrations/env.py`` (``autogenerate_plugins``).
"""

import logging

from alembic.autogenerate.api import AutogenContext
from alembic.operations import ops
from alembic.operations.ops import ModifyTableOps
from alembic.runtime.plugins import Plugin
from alembic.util import PriorityDispatchResult
from sqlalchemy import Index, Table, text
from sqlalchemy.sql.elements import quoted_name

log = logging.getLogger(__name__)

PLUGIN_NAME = "app.autogenerate.pg_opclass"

# Фактические классы по позициям ключа индекса и признак «класс по умолчанию для типа».
_ACTUAL_OPCLASSES_SQL = text(
    """
    SELECT idx.relname AS index_name, k.position, opc.opcname, opc.opcdefault
    FROM pg_index AS i
    JOIN pg_class AS idx ON idx.oid = i.indexrelid
    JOIN pg_class AS tbl ON tbl.oid = i.indrelid
    JOIN pg_namespace AS ns ON ns.oid = tbl.relnamespace
    CROSS JOIN LATERAL unnest(i.indclass::oid[]) WITH ORDINALITY AS k(opclass_oid, position)
    JOIN pg_opclass AS opc ON opc.oid = k.opclass_oid
    WHERE ns.nspname = COALESCE(:schema, current_schema()) AND tbl.relname = :table_name
    ORDER BY idx.relname, k.position
    """
)


def _expected_opclasses(index: Index) -> list[str | None]:
    """Класс оператора, заявленный в модели, по каждой позиции ключа; ``None`` — по умолчанию."""
    declared = index.dialect_options["postgresql"]["ops"] or {}
    return [declared.get(getattr(expression, "key", None)) for expression in index.expressions]


def _drop_op_restoring_actual_opclasses(index: Index, found: list[tuple[str, bool]]) -> ops.DropIndexOp:
    """
    ``drop_index`` для индекса из модели, чей откат (``downgrade``) вернёт классы из базы.

    По умолчанию обратная операция строится по самому индексу модели и создала бы его с новыми
    классами. Подменяем ``postgresql_ops`` на фактические: классы по умолчанию не пишем.
    """
    actual_ops = {
        key: opclass_name
        for expression, (opclass_name, is_default) in zip(index.expressions, found, strict=True)
        if (key := getattr(expression, "key", None)) and not is_default
    }
    drop_op = ops.DropIndexOp.from_index(index)
    drop_op.kw = {**drop_op.kw, "postgresql_ops": actual_ops}
    return drop_op


def _already_changed(modify_ops: ModifyTableOps, index_name: str | None) -> bool:
    """Alembic уже пересоздаёт этот индекс по другой причине — второй раз не добавляем."""
    return any(
        isinstance(operation, ops.DropIndexOp | ops.CreateIndexOp) and operation.index_name == index_name
        for operation in modify_ops.ops
    )


def _compare_index_opclasses(
    autogen_context: AutogenContext,
    modify_ops: ModifyTableOps,
    schema: str | None,
    tname: quoted_name | str,
    conn_table: Table | None,
    metadata_table: Table | None,
) -> PriorityDispatchResult:
    connection = autogen_context.connection
    if conn_table is None or metadata_table is None or connection is None:
        return PriorityDispatchResult.CONTINUE

    rows = connection.execute(_ACTUAL_OPCLASSES_SQL, {"schema": schema, "table_name": str(tname)}).all()
    actual: dict[str, list[tuple[str, bool]]] = {}
    for index_name, _position, opclass_name, is_default in rows:
        actual.setdefault(index_name, []).append((opclass_name, is_default))

    for index in metadata_table.indexes:
        if index.name not in actual or _already_changed(modify_ops, index.name):
            continue

        expected = _expected_opclasses(index)
        found = actual[index.name]
        if len(expected) != len(found):
            continue  # число ключей расходится — это видит штатное сравнение выражений

        for expected_name, (found_name, found_is_default) in zip(expected, found, strict=True):
            matches = found_is_default if expected_name is None else expected_name == found_name
            if matches:
                continue
            log.info(
                "Detected changed operator class of index %r on table %r: %r to %r",
                index.name,
                tname,
                found_name,
                expected_name or "<default>",
            )
            modify_ops.ops.append(_drop_op_restoring_actual_opclasses(index, found))
            modify_ops.ops.append(ops.CreateIndexOp.from_index(index))
            break

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(_compare_index_opclasses, "table", "index_opclasses", qualifier="postgresql")
