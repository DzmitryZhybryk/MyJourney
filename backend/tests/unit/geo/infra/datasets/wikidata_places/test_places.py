"""Unit-тесты сборки мест из ответов SPARQL."""

from collections import Counter

import pytest

from app.geo.domain.enums import PlaceKindEnum
from app.geo.infra.datasets.wikidata_places.places import ExportedPlace, ExportOutcomeEnum, collect_places
from app.shared.types import DictStrAny

# WKT в ответе Wikidata: сначала долгота, потом широта.
_TIAN_SHAN: DictStrAny = {
    "item": {"value": "http://www.wikidata.org/entity/Q5474"},
    "links": {"value": "99"},
    "coord": {"value": "Point(80.13 42.04)"},
    "en": {"value": "Tian Shan"},
    "ru": {"value": "Тянь-Шань"},
    "iso": {"value": "KZ"},
}
_BELUKHA: DictStrAny = {
    "item": {"value": "http://www.wikidata.org/entity/Q724367"},
    "links": {"value": "52"},
    "coord": {"value": "Point(86.59 49.81)"},
    "en": {"value": "Belukha"},
    "ru": {"value": "Белуха"},
    "iso": {"value": "RU"},
}


def test_collect_places_merges_rows_of_one_object() -> None:
    """collect_places: строки одного объекта (по стране на строку) сводятся в одно место, страны — по алфавиту."""
    bindings = [_TIAN_SHAN, {**_TIAN_SHAN, "iso": {"value": "CN"}}, {**_TIAN_SHAN, "iso": {"value": "KG"}}]

    places, outcomes = collect_places(class_bindings=[(PlaceKindEnum.MOUNTAIN_RANGE, bindings)])

    assert places == (
        ExportedPlace(
            external_id="Wikidata:Q5474",
            kind=PlaceKindEnum.MOUNTAIN_RANGE,
            name_en="Tian Shan",
            name_ru="Тянь-Шань",
            country_codes=("CN", "KG", "KZ"),
            latitude=42.04,
            longitude=80.13,
            notability=99,
        ),
    )
    assert outcomes == Counter({(PlaceKindEnum.MOUNTAIN_RANGE, ExportOutcomeEnum.KEPT): 1})


def test_collect_places_object_keeps_kind_of_narrowest_class() -> None:
    """collect_places: объект и в узком, и в широком классе → тип узкого, строки широкого класса не подмешиваются."""
    class_bindings = [
        (PlaceKindEnum.MOUNTAIN, [_BELUKHA]),
        (PlaceKindEnum.MOUNTAIN_RANGE, [{**_BELUKHA, "iso": {"value": "KZ"}}]),
    ]

    places, outcomes = collect_places(class_bindings=class_bindings)

    [place] = places
    assert (place.kind, place.country_codes) == (PlaceKindEnum.MOUNTAIN, ("RU",))
    assert outcomes == Counter({(PlaceKindEnum.MOUNTAIN, ExportOutcomeEnum.KEPT): 1})


@pytest.mark.parametrize(
    "coordinates",
    [("Point(86.59 49.81)", "Point(86.5 49.9)"), ("Point(86.5 49.9)", "Point(86.59 49.81)")],
    ids=["smallest-first", "smallest-last"],
)
def test_collect_places_picks_smallest_point_whatever_the_order(coordinates: tuple[str, str]) -> None:
    """collect_places: из нескольких точек берётся наименьшая по (широта, долгота), порядок строк не важен."""
    bindings = [{**_BELUKHA, "coord": {"value": coordinate}} for coordinate in coordinates]

    [place], _ = collect_places(class_bindings=[(PlaceKindEnum.MOUNTAIN, bindings)])

    assert (place.latitude, place.longitude) == (49.81, 86.59)


@pytest.mark.parametrize(
    ("binding", "outcome"),
    [
        (
            {**_BELUKHA, "coord": {"value": "<http://www.wikidata.org/entity/Q405> Point(10.0 20.0)"}},
            ExportOutcomeEnum.NO_EARTH_POINT,
        ),
        ({key: value for key, value in _BELUKHA.items() if key != "iso"}, ExportOutcomeEnum.NO_COUNTRY),
        ({key: value for key, value in _BELUKHA.items() if key != "en"}, ExportOutcomeEnum.NO_EN),
        ({**_BELUKHA, "en": {"value": "(mountain)"}}, ExportOutcomeEnum.NO_EN),
        ({**_BELUKHA, "en": {"value": "B" * 201}}, ExportOutcomeEnum.NAME_TOO_LONG),
    ],
    ids=["moon", "no-country", "no-en", "en-only-qualifier", "en-too-long"],
)
def test_collect_places_drops_unusable_object(binding: DictStrAny, outcome: ExportOutcomeEnum) -> None:
    """collect_places: объект без земной точки, страны или годного имени en в датасет не попадает, причина в итоге."""
    places, outcomes = collect_places(class_bindings=[(PlaceKindEnum.MOUNTAIN, [binding])])

    assert places == ()
    assert outcomes == Counter({(PlaceKindEnum.MOUNTAIN, outcome): 1})


@pytest.mark.parametrize(
    ("binding", "names"),
    [
        ({**_BELUKHA, "en": {"value": "Belukha (mountain)"}, "ru": {"value": "Белуха (гора)"}}, ("Belukha", "Белуха")),
        ({**_BELUKHA, "en": {"value": "B" * 200}}, ("B" * 200, "Белуха")),
        ({**_BELUKHA, "ru": {"value": "Belukha"}}, ("Belukha", None)),
        ({key: value for key, value in _BELUKHA.items() if key != "ru"}, ("Belukha", None)),
    ],
    ids=["qualifiers", "en-fits-column", "latin-ru", "no-ru"],
)
def test_collect_places_cleans_labels(binding: DictStrAny, names: tuple[str, str | None]) -> None:
    """collect_places: уточнения в скобках срезаются; негодная или отсутствующая метка ru — место без русского имени."""
    [place], _ = collect_places(class_bindings=[(PlaceKindEnum.MOUNTAIN, [binding])])

    assert (place.name_en, place.name_ru) == names


def test_collect_places_sorts_places_by_external_id() -> None:
    """collect_places: места упорядочены по external_id, а не по порядку строк ответа."""
    bindings = [
        {**_BELUKHA, "item": {"value": "http://www.wikidata.org/entity/Q9"}},
        {**_BELUKHA, "item": {"value": "http://www.wikidata.org/entity/Q10"}},
    ]

    places, _ = collect_places(class_bindings=[(PlaceKindEnum.MOUNTAIN, bindings)])

    assert [place.external_id for place in places] == ["Wikidata:Q10", "Wikidata:Q9"]
