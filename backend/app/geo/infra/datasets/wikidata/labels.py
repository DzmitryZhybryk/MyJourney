import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

import httpx

from app.geo.infra.datasets.wikidata.sparql import fetch_sparql_bindings

_GEONAMES_PREFIX: Final[str] = "GeoNames:"

# Длина колонок имён в таблицах газеттира.
MAX_NAME_LENGTH: Final[int] = 200

# Столько id уходит в один SPARQL-запрос: длиннее — сервис начинает отвечать таймаутами.
_BATCH_SIZE: Final[int] = 400

# P1566 — свойство Wikidata «идентификатор GeoNames».
_QUERY_TEMPLATE: Final[str] = (
    "SELECT ?gn ?label WHERE {{ VALUES ?gn {{ {ids} }} ?item wdt:P1566 ?gn . "
    '?item rdfs:label ?label FILTER(lang(?label) = "ru") }}'
)

# Уточнение в конце метки: «Орай (город)», «Мушин (Нигерия)».
_TRAILING_QUALIFIER: Final[re.Pattern[str]] = re.compile(r"\s*\([^()]*\)$")

_CYRILLIC: Final[re.Pattern[str]] = re.compile(r"[А-Яа-яЁё]")


@dataclass(frozen=True, slots=True)
class EnrichmentReport:
    """Итог обогащения: сколько городов искали в Wikidata и чем кончился поиск."""

    candidates: int
    filled: int
    not_found: int
    ambiguous: int
    rejected: int


def geonames_id_of(*, external_id: str) -> str | None:
    """
    Достаёт id GeoNames из ключа города.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata

    Args:
        external_id: Ключ города с префиксом источника (``GeoNames:524901``)

    Returns:
        Id GeoNames или ``None``, если город не из GeoNames
    """
    if not external_id.startswith(_GEONAMES_PREFIX):
        return None

    return external_id.removeprefix(_GEONAMES_PREFIX)


def candidate_geonames_id(*, row: Mapping[str, str], min_population: int) -> str | None:
    """
    Решает, искать ли городу русское имя: имени нет, город из GeoNames и не меньше порога.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata

    Args:
        row: Строка файла датасета
        min_population: Нижняя граница населения

    Returns:
        Id GeoNames, по которому искать имя, или ``None``, если искать не нужно
    """
    population = row["population"]
    if row["name_ru"] or not population or int(population) < min_population:
        return None

    return geonames_id_of(external_id=row["external_id"])


def strip_qualifier(*, label: str) -> str:
    """
    Срезает уточнение в скобках в конце метки Wikidata и пробелы по краям: «Белуха (гора)» → «Белуха».

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - сборка новой версии датасета мест из Wikidata

    Args:
        label: Метка Wikidata

    Returns:
        Метка без уточнения
    """
    return _TRAILING_QUALIFIER.sub("", label).strip()


def acceptable_ru_name(*, label: str) -> str | None:
    """
    Чистит метку ``ru`` для русского имени города или места.

    Уточнение в скобках в конце срезается. Отбрасываются метки без кириллицы (латиница, оставленная
    в поле ``ru``), с запятой (имя с регионом: «Айвенго, штат Виктория, Австралия») и не
    помещающиеся в колонку имени.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: дописывание имён и поиск споров
        - сборка новой версии датасета мест из Wikidata

    Args:
        label: Метка ``ru`` объекта Wikidata

    Returns:
        Имя или ``None``, если метка не годится
    """
    name = strip_qualifier(label=label)
    if not _CYRILLIC.search(name) or "," in name or len(name) > MAX_NAME_LENGTH:
        return None

    return name


def acceptable_ru_names(*, labels: Iterable[str]) -> frozenset[str]:
    """
    Отбирает из меток Wikidata те, что годятся в русское имя города (правила — ``acceptable_ru_name``).

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: дописывание имён и поиск споров

    Args:
        labels: Метки ``ru`` всех объектов Wikidata с одним id GeoNames

    Returns:
        Годные имена; больше одного — id привязан к разным объектам
    """
    names = (acceptable_ru_name(label=label) for label in labels)
    return frozenset(name for name in names if name is not None)


def fetch_ru_labels(*, geonames_ids: Iterable[str], http_client: httpx.Client) -> dict[str, frozenset[str]]:
    """
    Запрашивает у Wikidata метки ``ru`` объектов по их id GeoNames.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata

    Args:
        geonames_ids: Id GeoNames
        http_client: HTTP-клиент

    Returns:
        Метки по id GeoNames; id без единой метки в результат не попадают

    Raises:
        httpx.HTTPError: запрос к Wikidata не удался, в том числе после всех повторов
    """
    ids = list(geonames_ids)
    labels: defaultdict[str, set[str]] = defaultdict(set)
    for start in range(0, len(ids), _BATCH_SIZE):
        batch = ids[start : start + _BATCH_SIZE]
        query = _QUERY_TEMPLATE.format(ids=" ".join(f'"{geonames_id}"' for geonames_id in batch))
        for binding in fetch_sparql_bindings(query=query, http_client=http_client):
            labels[binding["gn"]["value"]].add(binding["label"]["value"])

    return {geonames_id: frozenset(values) for geonames_id, values in labels.items()}


def enrich_rows(
    *,
    rows: Iterable[Mapping[str, str]],
    labels: Mapping[str, frozenset[str]],
    min_population: int,
) -> tuple[tuple[dict[str, str], ...], EnrichmentReport]:
    """
    Дописывает русские имена городам без них; уже заполненные имена не меняются.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata

    Args:
        rows: Строки файла датасета
        labels: Метки Wikidata по id GeoNames (см. ``fetch_ru_labels``)
        min_population: Нижняя граница населения для поиска имени

    Returns:
        Строки в исходном порядке и итог обогащения
    """
    enriched: list[dict[str, str]] = []
    candidates = filled = not_found = ambiguous = rejected = 0
    for row in rows:
        new_row = dict(row)
        geonames_id = candidate_geonames_id(row=row, min_population=min_population)
        if geonames_id is not None:
            candidates += 1
            found = labels.get(geonames_id, frozenset())
            names = acceptable_ru_names(labels=found)
            if len(names) == 1:
                [new_row["name_ru"]] = names
                filled += 1
            elif len(names) > 1:
                ambiguous += 1
            elif found:
                rejected += 1
            else:
                not_found += 1

        enriched.append(new_row)

    report = EnrichmentReport(
        candidates=candidates,
        filled=filled,
        not_found=not_found,
        ambiguous=ambiguous,
        rejected=rejected,
    )
    return tuple(enriched), report
