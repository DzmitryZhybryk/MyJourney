"""
Снапшот OpenAPI-схемы.

``backend/openapi.json`` — вход кодогенерации фронтового SDK, поэтому он обязан совпадать с
тем, что отдаёт приложение. Обновить снапшот: ``make openapi-dump``.
"""

import json
import os
from collections import Counter
from pathlib import Path
from typing import Final

from app.shared.types import DictStrAny

_SNAPSHOT_PATH: Final[Path] = Path(__file__).resolve().parents[2] / "openapi.json"
_UPDATE_ENV_VAR: Final[str] = "UPDATE_OPENAPI"
# Версия пакета меняется на каждом бампе, а контракт API от неё не зависит — в снапшоте она константа.
_SNAPSHOT_VERSION: Final[str] = "snapshot"


def _render(schema: DictStrAny) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def test_openapi_snapshot_matches_app(openapi_schema: DictStrAny) -> None:
    """Закоммиченный openapi.json совпадает со схемой приложения с точностью до ``info.version``."""
    schema = {**openapi_schema, "info": {**openapi_schema["info"], "version": _SNAPSHOT_VERSION}}
    rendered = _render(schema)

    if os.environ.get(_UPDATE_ENV_VAR):
        _SNAPSHOT_PATH.write_text(rendered, encoding="utf-8")
        return

    assert _SNAPSHOT_PATH.read_text(encoding="utf-8") == rendered, (
        "openapi.json разошёлся со схемой приложения — прогони `make openapi-dump` и закоммить результат"
    )


def test_openapi_operation_ids_are_unique(openapi_schema: DictStrAny) -> None:
    """operationId уникальны — они становятся именами методов SDK, а FastAPI на дубль только warning'ует."""
    operation_ids = [
        operation["operationId"] for path_item in openapi_schema["paths"].values() for operation in path_item.values()
    ]

    duplicates = sorted(operation_id for operation_id, count in Counter(operation_ids).items() if count > 1)

    assert not duplicates, f"Дублирующиеся operationId: {duplicates}"
