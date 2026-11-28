"""Unit-тесты локального кеша файлов датасетов: скачивание, проверка sha256, повторное использование."""

from pathlib import Path

import httpx
import pytest

from app.geo.infra.datasets.cache import ensure_cached
from app.geo.infra.datasets.exceptions import DatasetChecksumError
from tests.builders import make_dataset_spec

_CONTENT = b"dataset-bytes"


def test_ensure_cached_downloads_verified_file(tmp_path: Path) -> None:
    """ensure_cached: файла нет → скачивает, кладёт под итоговым именем, мусора рядом не остаётся."""
    spec = make_dataset_spec(content=_CONTENT)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=_CONTENT))

    with httpx.Client(transport=transport) as http_client:
        path = ensure_cached(spec=spec, cache_dir=tmp_path, http_client=http_client)

    assert path.read_bytes() == _CONTENT
    assert [entry.name for entry in tmp_path.iterdir()] == [path.name]


def test_ensure_cached_checksum_mismatch_raises_and_leaves_nothing(tmp_path: Path) -> None:
    """ensure_cached: скачанное не совпало с sha256 манифеста → ошибка, в кеше пусто."""
    spec = make_dataset_spec(content=_CONTENT)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"tampered"))

    with httpx.Client(transport=transport) as http_client, pytest.raises(DatasetChecksumError):
        ensure_cached(spec=spec, cache_dir=tmp_path, http_client=http_client)

    assert list(tmp_path.iterdir()) == []


def test_ensure_cached_http_error_leaves_nothing(tmp_path: Path) -> None:
    """ensure_cached: сервер ответил ошибкой → исключение httpx, недокачанный файл удалён."""
    spec = make_dataset_spec(content=_CONTENT)
    transport = httpx.MockTransport(lambda request: httpx.Response(404))

    with httpx.Client(transport=transport) as http_client, pytest.raises(httpx.HTTPStatusError):
        ensure_cached(spec=spec, cache_dir=tmp_path, http_client=http_client)

    assert list(tmp_path.iterdir()) == []


def test_ensure_cached_reuses_valid_cached_file_without_download(tmp_path: Path) -> None:
    """ensure_cached: в кеше целый файл → сеть не трогается."""
    spec = make_dataset_spec(content=_CONTENT)
    first_path = tmp_path / f"{spec.name}-{spec.version}.csv.gz"
    first_path.write_bytes(_CONTENT)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=_CONTENT)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        path = ensure_cached(spec=spec, cache_dir=tmp_path, http_client=http_client)

    assert path == first_path
    assert requests == []


def test_ensure_cached_redownloads_corrupted_cached_file(tmp_path: Path) -> None:
    """ensure_cached: файл в кеше битый (прерванный прошлый запуск) → скачивается заново."""
    spec = make_dataset_spec(content=_CONTENT)
    (tmp_path / f"{spec.name}-{spec.version}.csv.gz").write_bytes(b"trunc")
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=_CONTENT))

    with httpx.Client(transport=transport) as http_client:
        path = ensure_cached(spec=spec, cache_dir=tmp_path, http_client=http_client)

    assert path.read_bytes() == _CONTENT
