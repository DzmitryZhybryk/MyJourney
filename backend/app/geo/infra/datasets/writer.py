import csv
import gzip
import hashlib
import io
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path


def write_dataset_file(*, path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> str:
    """
    Пишет файл датасета: CSV с заголовком, сжатый gzip.

    Пустое имя и mtime=0 в gzip-заголовке: одинаковые строки дают побайтно одинаковый файл и тот же
    sha256, куда бы и когда его ни записали.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - сборка новой версии датасета мест из Wikidata

    Args:
        path: Куда записать ``.csv.gz``
        fieldnames: Колонки в порядке заголовка
        rows: Строки файла

    Returns:
        sha256 записанного файла — его прописывают в манифест
    """
    with (
        path.open("wb") as raw_output,
        gzip.GzipFile(filename="", fileobj=raw_output, mode="wb", mtime=0) as gzip_output,
        io.TextIOWrapper(gzip_output, encoding="utf-8", newline="") as output_file,
    ):
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    return hashlib.sha256(path.read_bytes()).hexdigest()
