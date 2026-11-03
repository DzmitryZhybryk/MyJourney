"""Unit-тесты обогащения датасета русскими именами из Wikidata."""

import json
from urllib.parse import parse_qs

import httpx
import pytest

from app.geo.infra.datasets.wikidata.labels import (
    EnrichmentReport,
    acceptable_ru_name,
    acceptable_ru_names,
    enrich_rows,
    fetch_ru_labels,
)


def test_enrich_rows_fills_missing_name_from_single_label() -> None:
    """enrich_rows: у крупного города нет русского имени, в Wikidata одна метка → имя дописано."""
    rows = [{"external_id": "GeoNames:1", "name_en": "Kukshi", "name_ru": "", "population": "128000"}]

    enriched, report = enrich_rows(rows=rows, labels={"1": frozenset({"Кукши"})}, min_population=100_000)

    assert enriched == ({"external_id": "GeoNames:1", "name_en": "Kukshi", "name_ru": "Кукши", "population": "128000"},)
    assert report == EnrichmentReport(candidates=1, filled=1, not_found=0, ambiguous=0, rejected=0)


def test_enrich_rows_keeps_existing_name() -> None:
    """enrich_rows: русское имя уже есть → не меняется, даже если Wikidata пишет иначе."""
    rows = [{"external_id": "GeoNames:1", "name_en": "Meerut", "name_ru": "Меерут", "population": "1300000"}]

    enriched, report = enrich_rows(rows=rows, labels={"1": frozenset({"Мератх"})}, min_population=100_000)

    assert enriched[0]["name_ru"] == "Меерут"
    assert report.candidates == 0


@pytest.mark.parametrize(
    ("population", "expected_name"),
    [("100000", "Город"), ("99999", ""), ("", "")],
    ids=["at-threshold", "below-threshold", "no-population"],
)
def test_enrich_rows_respects_population_threshold(population: str, expected_name: str) -> None:
    """enrich_rows: имя ищется от порога населения включительно; меньше или без населения — нет."""
    rows = [{"external_id": "GeoNames:1", "name_en": "Town", "name_ru": "", "population": population}]

    enriched, _ = enrich_rows(rows=rows, labels={"1": frozenset({"Город"})}, min_population=100_000)

    assert enriched[0]["name_ru"] == expected_name


def test_enrich_rows_skips_cities_not_from_geonames() -> None:
    """enrich_rows: ключ не GeoNames → искать имя не по чему, строка не трогается."""
    rows = [{"external_id": "OSM:1", "name_en": "Town", "name_ru": "", "population": "500000"}]

    enriched, report = enrich_rows(rows=rows, labels={"1": frozenset({"Город"})}, min_population=100_000)

    assert enriched[0]["name_ru"] == ""
    assert report.candidates == 0


def test_enrich_rows_counts_why_name_was_not_filled() -> None:
    """enrich_rows: разные годные метки, только негодные метки, нет меток — имя пустое, причина в отчёте."""
    rows = [
        {"external_id": "GeoNames:1", "name_en": "Sodermalm", "name_ru": "", "population": "130000"},
        {"external_id": "GeoNames:2", "name_en": "Telica", "name_ru": "", "population": "120000"},
        {"external_id": "GeoNames:3", "name_en": "Evaton", "name_ru": "", "population": "725000"},
    ]
    labels = {"1": frozenset({"Стокгольм", "Сёдермальм"}), "2": frozenset({"Telica"})}

    enriched, report = enrich_rows(rows=rows, labels=labels, min_population=100_000)

    assert [row["name_ru"] for row in enriched] == ["", "", ""]
    assert report == EnrichmentReport(candidates=3, filled=0, not_found=1, ambiguous=1, rejected=1)


def test_enrich_rows_fills_when_only_one_label_is_acceptable() -> None:
    """enrich_rows: негодная метка рядом с годной не делает id неоднозначным — берётся годная."""
    rows = [{"external_id": "GeoNames:1", "name_en": "Frankston", "name_ru": "", "population": "140000"}]
    labels = {"1": frozenset({"Франкстон, Виктория", "Франкстон"})}

    enriched, _ = enrich_rows(rows=rows, labels=labels, min_population=100_000)

    assert enriched[0]["name_ru"] == "Франкстон"


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ({"Орай (город)"}, {"Орай"}),
        ({"Шерпур (город, Бангладеш)"}, {"Шерпур"}),
        ({"Мушин (Нигерия)", "Мушин"}, {"Мушин"}),
        ({"Стокгольм", "Сёдермальм"}, {"Стокгольм", "Сёдермальм"}),
        ({"La Paz Centro"}, set()),
        ({"Айвенго, штат Виктория, Австралия"}, set()),
        (set(), set()),
    ],
    ids=["qualifier", "qualifier-with-comma", "same-after-strip", "different", "latin", "comma", "empty"],
)
def test_acceptable_ru_names(labels: set[str], expected: set[str]) -> None:
    """acceptable_ru_names: скобки в конце срезаются; латиница и имена с запятой отбрасываются."""
    assert acceptable_ru_names(labels=labels) == expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Белуха (гора)", "Белуха"),
        (" Белуха ", "Белуха"),
        ("Б" * 200, "Б" * 200),
        ("Б" * 201, None),
        ("Belukha", None),
        ("Белуха, Алтай", None),
        ("(гора)", None),
    ],
    ids=["qualifier", "whitespace", "fits-column", "too-long", "latin", "comma", "only-qualifier"],
)
def test_acceptable_ru_name(label: str, expected: str | None) -> None:
    """acceptable_ru_name: уточнение и пробелы по краям срезаются; не влезающее в колонку имени отбрасывается."""
    assert acceptable_ru_name(label=label) == expected


def test_fetch_ru_labels_batches_ids_and_groups_labels() -> None:
    """fetch_ru_labels: id идут пачками по 400, метки собираются по id GeoNames."""
    requested_batches: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = parse_qs(request.content.decode())["query"][0]
        ids = query.split("VALUES ?gn {")[1].split("}")[0].split()
        requested_batches.append([geonames_id.strip('"') for geonames_id in ids])
        bindings = [
            {"gn": {"value": "1"}, "label": {"value": "Москва"}},
            {"gn": {"value": "1"}, "label": {"value": "Москва (город)"}},
        ]
        return httpx.Response(200, content=json.dumps({"results": {"bindings": bindings}}))

    geonames_ids = [str(number) for number in range(1, 402)]
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        labels = fetch_ru_labels(geonames_ids=geonames_ids, http_client=http_client)

    assert [len(batch) for batch in requested_batches] == [400, 1]
    assert [geonames_id for batch in requested_batches for geonames_id in batch] == geonames_ids
    assert labels == {"1": frozenset({"Москва", "Москва (город)"})}
