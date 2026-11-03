"""
CLI: выгружает места (озёра, горы, хребты…) из Wikidata в файл датасета формата ``places``.

``python -m app.geo.infra.datasets.wikidata_places --output <путь>.csv.gz [--min-sitelinks N]``

Результат — новая версия датасета: её заливают ассетом GitHub Release и прописывают в манифест.
"""

import argparse
from pathlib import Path
from typing import Final

import httpx

from app.geo.domain.enums import PlaceKindEnum
from app.geo.infra.datasets.wikidata_places.places import ExportedPlace, collect_places
from app.geo.infra.datasets.wikidata_places.query import PLACE_CLASSES, fetch_class_bindings
from app.geo.infra.datasets.writer import write_dataset_file
from app.shared.logging import configure_logging, get_logger
from app.shared.types import DictStrAny

logger = get_logger(__name__)

_HTTP_TIMEOUT_SECONDS: Final[float] = 120.0
_DEFAULT_MIN_SITELINKS: Final[int] = 4

_FIELDNAMES: Final[tuple[str, ...]] = (
    "external_id",
    "kind",
    "name_en",
    "name_ru",
    "country_codes",
    "latitude",
    "longitude",
    "notability",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Выгрузить места из Wikidata в датасет формата places")
    parser.add_argument("--output", type=Path, required=True, help="Куда записать .csv.gz")
    parser.add_argument(
        "--min-sitelinks",
        type=int,
        default=_DEFAULT_MIN_SITELINKS,
        help="Нижняя граница числа сайтов Wikimedia со статьёй об объекте",
    )
    return parser.parse_args()


def main() -> None:
    """
    Запрашивает классы мест у Wikidata, сводит ответы в места и пишет файл датасета.

    Scenarios:
        - сборка новой версии датасета мест из Wikidata
    """
    configure_logging(include_debug=False)
    args = _parse_args()
    class_bindings: list[tuple[PlaceKindEnum, tuple[DictStrAny, ...]]] = []
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as http_client:
        for kind, class_qids in PLACE_CLASSES:
            for class_qid in class_qids:
                bindings = fetch_class_bindings(
                    class_qid=class_qid,
                    min_sitelinks=args.min_sitelinks,
                    http_client=http_client,
                )
                logger.info("geo.wikidata_places.class_fetched", kind=kind, class_qid=class_qid, rows=len(bindings))
                class_bindings.append((kind, bindings))

    places, outcomes = collect_places(class_bindings=class_bindings)
    sha256 = write_dataset_file(
        path=args.output,
        fieldnames=_FIELDNAMES,
        rows=(_to_csv_row(place=place) for place in places),
    )
    logger.info(
        "geo.wikidata_places.exported",
        output=str(args.output),
        sha256=sha256,
        places=len(places),
        outcomes={f"{kind}.{outcome}": count for (kind, outcome), count in sorted(outcomes.items())},
    )


def _to_csv_row(*, place: ExportedPlace) -> dict[str, str | float | int]:
    return {
        "external_id": place.external_id,
        "kind": place.kind,
        "name_en": place.name_en,
        "name_ru": place.name_ru or "",
        "country_codes": ",".join(place.country_codes),
        "latitude": place.latitude,
        "longitude": place.longitude,
        "notability": place.notability,
    }


if __name__ == "__main__":
    main()
