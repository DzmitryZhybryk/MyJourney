import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

MANIFEST_PATH: Final[Path] = Path(__file__).with_name("manifest.toml")


class DatasetFormatEnum(StrEnum):
    """Формат файла датасета (FORMAT.md): от него зависят колонки файла и таблица, куда он грузится."""

    CITIES = "cities"
    PLACES = "places"


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Датасет газеттира из манифеста: что загрузить, откуда и как проверить целостность файла."""

    name: str
    format: DatasetFormatEnum
    version: str
    url: str
    sha256: str


def read_manifest(*, path: Path = MANIFEST_PATH) -> tuple[DatasetSpec, ...]:
    """
    Читает манифест датасетов.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
        - сборка новой версии датасета с русскими названиями из Wikidata: исходный файл

    Args:
        path: Путь к TOML-манифесту (по умолчанию — ``manifest.toml`` рядом с модулем)

    Returns:
        Датасеты в порядке объявления

    Raises:
        KeyError: у датасета нет обязательного поля, в том числе ``format``
        ValueError: ``format`` датасета не из ``DatasetFormatEnum``
    """
    with path.open("rb") as manifest_file:
        manifest = tomllib.load(manifest_file)

    return tuple(
        DatasetSpec(
            name=dataset["name"],
            format=DatasetFormatEnum(dataset["format"]),
            version=dataset["version"],
            url=dataset["url"],
            sha256=dataset["sha256"],
        )
        for dataset in manifest["dataset"]
    )
