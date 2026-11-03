"""Unit-тесты записи файла датасета."""

import csv
import gzip
import hashlib
from pathlib import Path

from app.geo.infra.datasets.writer import write_dataset_file

_FIELDNAMES = ("external_id", "name_en", "name_ru")
_ROWS = ({"external_id": "Wikidata:Q724367", "name_en": "Belukha", "name_ru": "Белуха"},)


def test_write_dataset_file_writes_gzipped_csv_and_returns_its_sha256(tmp_path: Path) -> None:
    """write_dataset_file: CSV с заголовком в gzip читается обратно; возвращён sha256 записанного файла."""
    path = tmp_path / "places.csv.gz"

    sha256 = write_dataset_file(path=path, fieldnames=_FIELDNAMES, rows=_ROWS)

    with gzip.open(path, "rt", encoding="utf-8", newline="") as dataset_file:
        rows = tuple(csv.DictReader(dataset_file))

    assert rows == _ROWS
    assert sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_write_dataset_file_bytes_do_not_depend_on_file_name_or_time(tmp_path: Path) -> None:
    """write_dataset_file: те же строки под другим именем — те же байты; в gzip-заголовке нет ни имени, ни времени."""
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"

    write_dataset_file(path=first, fieldnames=_FIELDNAMES, rows=_ROWS)
    write_dataset_file(path=second, fieldnames=_FIELDNAMES, rows=_ROWS)

    content = first.read_bytes()
    assert second.read_bytes() == content
    # RFC 1952: байты 4–7 заголовка — MTIME, ноль значит «время не записано».
    assert content[4:8] == bytes(4)
