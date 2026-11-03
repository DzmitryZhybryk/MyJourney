"""
CLI: дописывает русские имена в файл датасета из Wikidata и применяет решения по спорам с GeoNames.

``python -m app.geo.infra.datasets.wikidata --output <путь>.csv.gz [--input <путь>] [--min-population N]
[--disputes-out <споры>.json] [--record <вердикты>.json]``

Без ``--input`` берёт файл датасета из ``manifest.toml`` (скачивает в кеш, если его там нет).
Результат — новая версия датасета: её заливают ассетом GitHub Release и прописывают в манифест.

Цикл арбитража: сборка с ``--disputes-out`` выгружает споры без решения → арбитр выносит вердикты →
сборка с ``--record`` дописывает их в ``ru_name_decisions.csv`` и применяет.
"""

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Final

import httpx

from app.geo.infra.datasets.cache import ensure_cached
from app.geo.infra.datasets.manifest import DatasetFormatEnum, read_manifest
from app.geo.infra.datasets.wikidata.disputes import (
    ArbiterVerdict,
    RuNameDispute,
    apply_decisions,
    find_disputes,
    merge_decisions,
    read_decisions,
    record_verdicts,
    write_decisions,
)
from app.geo.infra.datasets.wikidata.labels import (
    candidate_geonames_id,
    enrich_rows,
    fetch_ru_labels,
    geonames_id_of,
)
from app.geo.infra.datasets.writer import write_dataset_file
from app.shared.logging import configure_logging, get_logger
from app.shared.settings import settings
from app.shared.types import DictStrAny

logger = get_logger(__name__)

_HTTP_TIMEOUT_SECONDS: Final[float] = 120.0
_DEFAULT_MIN_POPULATION: Final[int] = 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Дописать русские имена городов из Wikidata")
    parser.add_argument("--output", type=Path, required=True, help="Куда записать новый .csv.gz")
    parser.add_argument("--input", type=Path, help="Исходный .csv.gz; по умолчанию — датасет из манифеста")
    parser.add_argument("--min-population", type=int, default=_DEFAULT_MIN_POPULATION)
    parser.add_argument("--disputes-out", type=Path, help="Куда выгрузить споры без решения (JSON) для арбитража")
    parser.add_argument(
        "--record",
        type=Path,
        help="Вердикты арбитра (JSON: external_id, name_ru, decided_by, reason) — дописать в файл решений",
    )
    return parser.parse_args()


def main() -> None:
    """
    Читает датасет, дописывает имена из Wikidata и пишет новый файл.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - выгрузка споров о русских названиях на арбитраж
        - запись вердиктов арбитра в файл решений
    """
    configure_logging(include_debug=False)
    args = _parse_args()
    with httpx.Client(follow_redirects=True, timeout=_HTTP_TIMEOUT_SECONDS) as http_client:
        input_path: Path = args.input or ensure_cached(
            spec=next(dataset for dataset in read_manifest() if dataset.format is DatasetFormatEnum.CITIES),
            cache_dir=settings.GEO_DATASETS_CACHE_DIR,
            http_client=http_client,
        )
        with gzip.open(input_path, "rt", encoding="utf-8", newline="") as input_file:
            reader = csv.DictReader(input_file)
            fieldnames = list(reader.fieldnames or ())
            rows = list(reader)

        # Метки нужны и пустым именам (дописать), и заполненным (найти споры с GeoNames).
        geonames_ids = [
            geonames_id
            for row in rows
            if (geonames_id := geonames_id_of(external_id=row["external_id"])) is not None
            and (row["name_ru"] or candidate_geonames_id(row=row, min_population=args.min_population))
        ]
        labels = fetch_ru_labels(geonames_ids=geonames_ids, http_client=http_client)

    disputes = find_disputes(rows=rows, labels=labels)
    decisions = read_decisions()
    if args.record:
        verdicts = [ArbiterVerdict(**entry) for entry in json.loads(args.record.read_text(encoding="utf-8"))]
        recorded = record_verdicts(verdicts=verdicts, rows=rows, disputes=disputes)
        decisions = merge_decisions(decisions=decisions, recorded=recorded)
        write_decisions(decisions=decisions.values())

    decided, unresolved, disputes_report = apply_decisions(rows=rows, disputes=disputes, decisions=decisions)
    enriched, report = enrich_rows(rows=decided, labels=labels, min_population=args.min_population)
    if args.disputes_out:
        args.disputes_out.write_text(
            json.dumps([_dispute_to_json(dispute=dispute) for dispute in unresolved], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    sha256 = write_dataset_file(path=args.output, fieldnames=fieldnames, rows=enriched)
    logger.info(
        "geo.wikidata.enriched",
        input=str(input_path),
        output=str(args.output),
        sha256=sha256,
        candidates=report.candidates,
        filled=report.filled,
        not_found=report.not_found,
        ambiguous=report.ambiguous,
        rejected=report.rejected,
        disputes=disputes_report.disputes,
        disputes_resolved=disputes_report.resolved,
        disputes_unresolved=disputes_report.unresolved,
        corrected=disputes_report.corrected,
        stale_decisions=disputes_report.stale,
    )


def _dispute_to_json(*, dispute: RuNameDispute) -> DictStrAny:
    return {
        "id": dispute.external_id,
        "name_en": dispute.name_en,
        "country": dispute.country_code,
        "population": dispute.population,
        "geonames_ru": dispute.geonames_ru,
        "wikidata_ru": sorted(dispute.wikidata_ru),
    }


if __name__ == "__main__":
    main()
