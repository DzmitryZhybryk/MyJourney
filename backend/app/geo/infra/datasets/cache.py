import hashlib
import tempfile
from pathlib import Path
from typing import Final

import httpx

from app.geo.infra.datasets.exceptions import DatasetChecksumError
from app.geo.infra.datasets.manifest import DatasetSpec

_CHUNK_SIZE: Final[int] = 1024 * 1024


def ensure_cached(*, spec: DatasetSpec, cache_dir: Path, http_client: httpx.Client) -> Path:
    """
    Возвращает файл датасета из кеша, при необходимости скачивая его.

    Файл из кеша перепроверяется по sha256; битый удаляется и скачивается заново. Скачанный файл
    попадает в кеш только после проверки, атомарным переименованием.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
        - сборка новой версии датасета с русскими названиями из Wikidata: исходный файл

    Args:
        spec: Датасет из манифеста
        cache_dir: Папка кеша
        http_client: HTTP-клиент, следующий редиректам

    Returns:
        Путь к файлу датасета, совпадающему с ``spec.sha256``

    Raises:
        DatasetChecksumError: скачанный файл не совпал с контрольной суммой
        httpx.HTTPError: файл не удалось скачать
    """
    path = cache_dir / f"{spec.name}-{spec.version}.csv.gz"
    if path.exists():
        if _sha256_of(path=path) == spec.sha256:
            return path

        path.unlink()

    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=cache_dir, prefix=f".{path.name}.", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        try:
            with http_client.stream("GET", spec.url) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=_CHUNK_SIZE):
                    temp_file.write(chunk)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    actual_sha256 = _sha256_of(path=temp_path)
    if actual_sha256 != spec.sha256:
        temp_path.unlink()
        raise DatasetChecksumError(spec=spec, actual_sha256=actual_sha256)

    temp_path.replace(path)
    return path


def _sha256_of(*, path: Path) -> str:
    """
    Считает sha256 файла потоково, не загружая его в память целиком.

    Scenarios:
        - загрузка газеттира в базу: проверка файла из кеша
        - сборка новой версии датасета с русскими названиями из Wikidata: проверка исходного файла
    """
    digest = hashlib.sha256()
    with path.open("rb") as dataset_file:
        for chunk in iter(lambda: dataset_file.read(_CHUNK_SIZE), b""):
            digest.update(chunk)

    return digest.hexdigest()
