"""Unit-тесты разбора CSV датасета в строки ``geo_cities`` и ``geo_places``."""

import pytest

from app.geo.infra.datasets.exceptions import (
    DatasetColumnsError,
    DuplicateCountryCodeError,
    InvalidCountryCodeError,
    InvalidExternalIdError,
    InvalidNumberError,
    MissingCountryCodeError,
    MissingEnglishNameError,
    UnknownPlaceKindError,
)
from app.geo.infra.datasets.identity import gazetteer_id_for
from app.geo.infra.datasets.rows import iter_city_rows, iter_place_rows

_HEADER = "external_id,name_en,name_ru,country_code,latitude,longitude,population"
_PLACE_HEADER = "external_id,kind,name_en,name_ru,country_codes,latitude,longitude,notability"


def test_iter_city_rows_parses_full_row() -> None:
    """iter_city_rows: строка файла → значения колонок, id выведен из external_id."""
    lines = [_HEADER, "GeoNames:524901,Moscow,Москва,RU,55.75,37.62,10000000"]

    [row] = list(iter_city_rows(lines=lines))

    assert row == (
        gazetteer_id_for(external_id="GeoNames:524901"),
        "GeoNames:524901",
        "Moscow",
        "Москва",
        "RU",
        55.75,
        37.62,
        10_000_000,
    )


def test_iter_city_rows_empty_optional_cells_become_none() -> None:
    """iter_city_rows: пустые name_ru и population — NULL, а не пустая строка."""
    lines = [_HEADER, "GeoNames:1,Town,,FR,43.4,3.4,"]

    [row] = list(iter_city_rows(lines=lines))

    assert row[3] is None
    assert row[7] is None


def test_iter_city_rows_accepts_columns_in_any_order() -> None:
    """iter_city_rows: порядок колонок в файле не важен — важен набор."""
    lines = [
        "name_en,external_id,name_ru,country_code,latitude,longitude,population",
        "Moscow,GeoNames:524901,Москва,RU,55.75,37.62,10000000",
    ]

    [row] = list(iter_city_rows(lines=lines))

    assert row[1] == "GeoNames:524901"
    assert row[2] == "Moscow"


@pytest.mark.parametrize(
    "header",
    [
        "external_id,name_en,country_code,latitude,longitude,population",
        f"{_HEADER},name_de",
        "external_id,kind,name_en,name_ru,country_code,latitude,longitude,population",
    ],
    ids=["missing-column", "extra-column", "legacy-kind-column"],
)
def test_iter_city_rows_rejects_unexpected_columns(header: str) -> None:
    """iter_city_rows: набор колонок не как в формате → DatasetColumnsError до разбора строк."""
    with pytest.raises(DatasetColumnsError):
        list(iter_city_rows(lines=[header]))


def test_iter_city_rows_rejects_city_without_english_name() -> None:
    """iter_city_rows: город без английского названия → MissingEnglishNameError с его ключом."""
    lines = [_HEADER, "GeoNames:7,,Москва,RU,55.75,37.62,1"]

    with pytest.raises(MissingEnglishNameError, match="GeoNames:7"):
        list(iter_city_rows(lines=lines))


def test_iter_city_rows_rejects_city_without_country() -> None:
    """iter_city_rows: город без страны → MissingCountryCodeError с его ключом, а не NULL в базе."""
    lines = [_HEADER, "GeoNames:8,Town,,,55.75,37.62,1"]

    with pytest.raises(MissingCountryCodeError, match="GeoNames:8"):
        list(iter_city_rows(lines=lines))


@pytest.mark.parametrize(
    "external_id",
    ["", "524901", "GeoNames:", ":524901", "Geo Names:1"],
    ids=["empty", "no-source", "no-key", "empty-source", "space-in-source"],
)
def test_iter_city_rows_rejects_malformed_external_id(external_id: str) -> None:
    """iter_city_rows: ключ не вида <источник>:<ключ> → InvalidExternalIdError: из ключа выводится id города."""
    lines = [_HEADER, f"{external_id},Moscow,Москва,RU,55.75,37.62,1"]

    with pytest.raises(InvalidExternalIdError):
        list(iter_city_rows(lines=lines))


@pytest.mark.parametrize("country_code", ["ru", "R1", "RUS"], ids=["lowercase", "digit", "three-letters"])
def test_iter_city_rows_rejects_invalid_country_code(country_code: str) -> None:
    """iter_city_rows: страна не ISO 3166-1 alpha-2 → InvalidCountryCodeError с ключом города."""
    lines = [_HEADER, f"GeoNames:8,Town,,{country_code},55.75,37.62,1"]

    with pytest.raises(InvalidCountryCodeError, match="GeoNames:8"):
        list(iter_city_rows(lines=lines))


@pytest.mark.parametrize(
    ("latitude", "longitude", "population"),
    [
        ("90.1", "0", "1"),
        ("-90.1", "0", "1"),
        ("0", "180.1", "1"),
        ("0", "-180.1", "1"),
        ("nan", "0", "1"),
        ("0", "inf", "1"),
        ("north", "0", "1"),
        ("", "0", "1"),
        ("0", "0", "-1"),
        ("0", "0", "1.5"),
    ],
    ids=[
        "latitude-above",
        "latitude-below",
        "longitude-above",
        "longitude-below",
        "latitude-nan",
        "longitude-inf",
        "latitude-not-number",
        "latitude-empty",
        "population-negative",
        "population-fraction",
    ],
)
def test_iter_city_rows_rejects_invalid_number(latitude: str, longitude: str, population: str) -> None:
    """iter_city_rows: координата не число или вне пределов, население не целое ≥ 0 → InvalidNumberError с ключом."""
    lines = [_HEADER, f"GeoNames:9,Town,,FR,{latitude},{longitude},{population}"]

    with pytest.raises(InvalidNumberError, match="GeoNames:9"):
        list(iter_city_rows(lines=lines))


def test_iter_city_rows_accepts_numbers_on_bounds() -> None:
    """iter_city_rows: полюса, линия перемены дат и нулевое население — допустимые значения."""
    lines = [_HEADER, "GeoNames:1,South,,AQ,-90,180,0", "GeoNames:2,North,,NO,90,-180,0"]

    rows = list(iter_city_rows(lines=lines))

    assert [(row[5], row[6], row[7]) for row in rows] == [(-90.0, 180.0, 0), (90.0, -180.0, 0)]


def test_iter_place_rows_parses_full_row() -> None:
    """iter_place_rows: строка файла → значения колонок; страны — список для массива, id из external_id."""
    lines = [_PLACE_HEADER, 'Wikidata:Q5474,mountain_range,Tian Shan,Тянь-Шань,"CN,KG,KZ,UZ",42.04,80.13,99']

    [row] = list(iter_place_rows(lines=lines))

    assert row == (
        gazetteer_id_for(external_id="Wikidata:Q5474"),
        "Wikidata:Q5474",
        "mountain_range",
        "Tian Shan",
        "Тянь-Шань",
        ["CN", "KG", "KZ", "UZ"],
        42.04,
        80.13,
        99,
    )


def test_iter_place_rows_empty_name_ru_becomes_none() -> None:
    """iter_place_rows: пустое name_ru — NULL, а не пустая строка."""
    lines = [_PLACE_HEADER, "Wikidata:Q20614802,lake,Seven Lakes,,TJ,39.14,67.85,4"]

    [row] = list(iter_place_rows(lines=lines))

    assert row[4] is None


@pytest.mark.parametrize(
    "header",
    [
        "external_id,kind,name_en,name_ru,country_codes,latitude,longitude",
        f"{_PLACE_HEADER},population",
        _HEADER,
    ],
    ids=["missing-column", "extra-column", "cities-header"],
)
def test_iter_place_rows_rejects_unexpected_columns(header: str) -> None:
    """iter_place_rows: набор колонок не как в формате places → DatasetColumnsError до разбора строк."""
    with pytest.raises(DatasetColumnsError):
        list(iter_place_rows(lines=[header]))


def test_iter_place_rows_rejects_place_without_english_name() -> None:
    """iter_place_rows: место без английского названия → MissingEnglishNameError с его ключом."""
    lines = [_PLACE_HEADER, "Wikidata:Q1,lake,,Озеро,RU,55.0,37.0,5"]

    with pytest.raises(MissingEnglishNameError, match="Wikidata:Q1"):
        list(iter_place_rows(lines=lines))


def test_iter_place_rows_rejects_unknown_kind() -> None:
    """iter_place_rows: тип не из PlaceKindEnum → UnknownPlaceKindError с ключом места, а не мусор в базе."""
    lines = [_PLACE_HEADER, "Wikidata:Q2,river,Volga,Волга,RU,55.0,37.0,5"]

    with pytest.raises(UnknownPlaceKindError, match="Wikidata:Q2"):
        list(iter_place_rows(lines=lines))


def test_iter_place_rows_rejects_place_without_countries() -> None:
    """iter_place_rows: место без стран → MissingCountryCodeError с его ключом."""
    lines = [_PLACE_HEADER, "Wikidata:Q3,glacier,Glacier,,,-75.0,0.0,5"]

    with pytest.raises(MissingCountryCodeError, match="Wikidata:Q3"):
        list(iter_place_rows(lines=lines))


def test_iter_place_rows_rejects_malformed_external_id() -> None:
    """iter_place_rows: ключ без префикса источника → InvalidExternalIdError: из ключа выводится id места."""
    lines = [_PLACE_HEADER, "Q5474,mountain_range,Tian Shan,,KZ,42.04,80.13,99"]

    with pytest.raises(InvalidExternalIdError, match="Q5474"):
        list(iter_place_rows(lines=lines))


@pytest.mark.parametrize(
    "country_codes",
    [",", "RU,", ",RU", "RU,,KZ", "ru", "RU,KZ1"],
    ids=["only-separator", "trailing-separator", "leading-separator", "empty-between", "lowercase", "malformed-second"],
)
def test_iter_place_rows_rejects_invalid_country_code(country_codes: str) -> None:
    """iter_place_rows: пустой или не ISO 3166-1 alpha-2 код среди стран → InvalidCountryCodeError, а не '' в базе."""
    lines = [_PLACE_HEADER, f'Wikidata:Q4,lake,Lake,,"{country_codes}",55.0,37.0,5']

    with pytest.raises(InvalidCountryCodeError, match="Wikidata:Q4"):
        list(iter_place_rows(lines=lines))


@pytest.mark.parametrize("country_codes", ["RU,RU", "KZ,RU,KZ"], ids=["adjacent", "apart"])
def test_iter_place_rows_rejects_repeated_country(country_codes: str) -> None:
    """iter_place_rows: страна указана дважды → DuplicateCountryCodeError: выбор из двух одинаковых стран."""
    lines = [_PLACE_HEADER, f'Wikidata:Q5,lake,Lake,,"{country_codes}",55.0,37.0,5']

    with pytest.raises(DuplicateCountryCodeError, match="Wikidata:Q5"):
        list(iter_place_rows(lines=lines))


@pytest.mark.parametrize(
    ("latitude", "longitude", "notability"),
    [("91", "0", "5"), ("0", "-181", "5"), ("0", "nan", "5"), ("0", "0", "-1"), ("0", "0", ""), ("0", "0", "many")],
    ids=[
        "latitude-above",
        "longitude-below",
        "longitude-nan",
        "notability-negative",
        "notability-empty",
        "notability-not-number",
    ],
)
def test_iter_place_rows_rejects_invalid_number(latitude: str, longitude: str, notability: str) -> None:
    """iter_place_rows: координата не число или вне пределов, известность не целое ≥ 0 → InvalidNumberError с ключом."""
    lines = [_PLACE_HEADER, f"Wikidata:Q6,lake,Lake,,RU,{latitude},{longitude},{notability}"]

    with pytest.raises(InvalidNumberError, match="Wikidata:Q6"):
        list(iter_place_rows(lines=lines))
