"""
Guard: импорт ``application`` и ``domain`` любого домена не тянет FastAPI, Starlette и SQLAlchemy,
а точка входа воркера — FastAPI и Starlette.

Эти библиотеки приходят не из кода слоёв, а транзитивно — через ``__init__`` shared-пакета,
реэкспортирующего адаптер рядом с портом. tach такую цепочку не видит: ``app.shared`` для него
один модуль. Проверка идёт в чистом интерпретаторе (``-I``), потому что в процессе pytest эти
библиотеки уже загружены другими тестами; ``cwd`` — пустой каталог, чтобы настройки не прочитали
``.env``. Список модулей строится по файлам, а не импортом пакетов: импорт пакета сам и есть
проверяемое действие. Время ограничено потолком unit-уровня.
"""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Final

# tests/unit/shared/<этот файл> → backend/
_BACKEND_DIR: Final[Path] = Path(__file__).resolve().parents[3]
_FRAMEWORKS: Final[tuple[str, ...]] = ("fastapi", "starlette", "sqlalchemy")
_LAYERS: Final[tuple[str, ...]] = ("application", "domain")
_WEB_FRAMEWORKS: Final[tuple[str, ...]] = ("fastapi", "starlette")

_CHILD_CODE: Final[str] = """
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])
frameworks = json.loads(sys.argv[2])
for module_name in sys.argv[3:]:
    importlib.import_module(module_name)

print(json.dumps([name for name in frameworks if name in sys.modules]))
"""


def _frameworks_loaded_by(module_names: list[str], frameworks: tuple[str, ...], cwd: Path) -> list[str]:
    """Импортирует модули в чистом интерпретаторе и возвращает загруженные из ``frameworks``."""
    completed = subprocess.run(  # noqa: S603 — интерпретатор этого же процесса, аргументы — пути из репозитория
        [sys.executable, "-I", "-B", "-c", _CHILD_CODE, str(_BACKEND_DIR), json.dumps(frameworks), *module_names],
        cwd=cwd,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    loaded: list[str] = json.loads(completed.stdout)
    return loaded


def test_application_and_domain_import_without_web_and_orm_frameworks(
    tmp_path: Path,
    module_name_of: Callable[[Path], str],
) -> None:
    """Импорт всех модулей application/ и domain/ в чистом интерпретаторе не грузит FastAPI, Starlette, SQLAlchemy."""
    module_names = sorted(
        module_name_of(path) for layer in _LAYERS for path in (_BACKEND_DIR / "app").glob(f"*/{layer}/**/*.py")
    )

    assert module_names, "не найдено ни одного модуля application/ или domain/ — сломан поиск файлов"
    loaded = _frameworks_loaded_by(module_names, _FRAMEWORKS, tmp_path)
    assert loaded == [], f"загружены фреймворки при импорте {len(module_names)} модулей"


def test_worker_imports_without_web_frameworks(tmp_path: Path) -> None:
    """Импорт точки входа воркера в чистом интерпретаторе не грузит FastAPI и Starlette."""
    assert _frameworks_loaded_by(["app.worker"], _WEB_FRAMEWORKS, tmp_path) == []
