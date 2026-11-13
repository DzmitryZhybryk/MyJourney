import csv
import re
from collections.abc import Iterable, Iterator, Mapping
from typing import Final
from uuid import UUID

from app.geo.domain.enums import PlaceKindEnum
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

# Колонки geo_cities, которые заполняет загрузчик, — в порядке значений ``CityRow``.
CITY_TABLE_COLUMNS: Final[tuple[str, ...]] = (
    "id",
    "external_id",
    "name_en",
    "name_ru",
    "country_code",
    "latitude",
    "longitude",
    "population",
)

# Колонки файла датасета (FORMAT.md): те же, кроме id — он выводится из external_id.
CITY_CSV_COLUMNS: Final[frozenset[str]] = frozenset(CITY_TABLE_COLUMNS) - {"id"}

type CityRow = tuple[UUID, str, str, str | None, str, float, float, int | None]

# Колонки geo_places, которые заполняет загрузчик, — в порядке значений ``PlaceRow``.
PLACE_TABLE_COLUMNS: Final[tuple[str, ...]] = (
    "id",
    "external_id",
    "kind",
    "name_en",
    "name_ru",
    "country_codes",
    "latitude",
    "longitude",
    "notability",
)

PLACE_CSV_COLUMNS: Final[frozenset[str]] = frozenset(PLACE_TABLE_COLUMNS) - {"id"}

# Страны — list, а не tuple: psycopg пишет список как массив Postgres, а кортеж — как запись,
# которую COPY в колонку-массив не примет.
type PlaceRow = tuple[UUID, str, str, str, str | None, list[str], float, float, int]

_COUNTRY_CODES_SEPARATOR: Final[str] = ","

# Ключ объекта у поставщика с префиксом источника: «GeoNames:524901», «Wikidata:Q5474».
_EXTERNAL_ID: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9]*:\S+")

# ISO 3166-1 alpha-2.
_COUNTRY_CODE: Final[re.Pattern[str]] = re.compile(r"[A-Z]{2}")

_MAX_LATITUDE: Final[float] = 90.0
_MAX_LONGITUDE: Final[float] = 180.0


def iter_city_rows(*, lines: Iterable[str]) -> Iterator[CityRow]:
    """
    Разбирает CSV датасета в строки ``geo_cities``; пустые необязательные ячейки становятся NULL.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        lines: Строки CSV-файла, начиная с заголовка

    Yields:
        Значения колонок ``CITY_TABLE_COLUMNS`` для одного города

    Raises:
        DatasetColumnsError: колонки файла не совпадают с ``CITY_CSV_COLUMNS``
        InvalidExternalIdError: ``external_id`` не вида ``<источник>:<ключ>``
        MissingEnglishNameError: у города пустое ``name_en``
        MissingCountryCodeError: у города пустое ``country_code``
        InvalidCountryCodeError: ``country_code`` не ISO 3166-1 alpha-2
        InvalidNumberError: координата не число или вне пределов, ``population`` не целое ≥ 0
    """
    reader = csv.DictReader(lines)
    columns = frozenset(reader.fieldnames or ())
    if columns != CITY_CSV_COLUMNS:
        raise DatasetColumnsError(columns=columns)

    for row in reader:
        external_id = row["external_id"]
        _check_external_id(external_id=external_id)
        if not row["name_en"]:
            raise MissingEnglishNameError(external_id=external_id)

        if not row["country_code"]:
            raise MissingCountryCodeError(external_id=external_id)

        _check_country_code(external_id=external_id, country_code=row["country_code"])
        yield (
            gazetteer_id_for(external_id=external_id),
            external_id,
            row["name_en"],
            row["name_ru"] or None,
            row["country_code"],
            _parse_coordinate(row=row, column="latitude", limit=_MAX_LATITUDE),
            _parse_coordinate(row=row, column="longitude", limit=_MAX_LONGITUDE),
            _parse_count(row=row, column="population") if row["population"] else None,
        )


def iter_place_rows(*, lines: Iterable[str]) -> Iterator[PlaceRow]:
    """
    Разбирает CSV датасета в строки ``geo_places``; пустое ``name_ru`` становится NULL.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке

    Args:
        lines: Строки CSV-файла, начиная с заголовка

    Yields:
        Значения колонок ``PLACE_TABLE_COLUMNS`` для одного места

    Raises:
        DatasetColumnsError: колонки файла не совпадают с ``PLACE_CSV_COLUMNS``
        InvalidExternalIdError: ``external_id`` не вида ``<источник>:<ключ>``
        MissingEnglishNameError: у места пустое ``name_en``
        UnknownPlaceKindError: ``kind`` места не из ``PlaceKindEnum``
        MissingCountryCodeError: у места пустое ``country_codes``
        InvalidCountryCodeError: в ``country_codes`` код не ISO 3166-1 alpha-2, в том числе пустой
        DuplicateCountryCodeError: в ``country_codes`` код повторяется
        InvalidNumberError: координата не число или вне пределов, ``notability`` не целое ≥ 0
    """
    reader = csv.DictReader(lines)
    columns = frozenset(reader.fieldnames or ())
    if columns != PLACE_CSV_COLUMNS:
        raise DatasetColumnsError(columns=columns)

    for row in reader:
        external_id = row["external_id"]
        _check_external_id(external_id=external_id)
        if not row["name_en"]:
            raise MissingEnglishNameError(external_id=external_id)

        if row["kind"] not in PlaceKindEnum:
            raise UnknownPlaceKindError(external_id=external_id, kind=row["kind"])

        if not row["country_codes"]:
            raise MissingCountryCodeError(external_id=external_id)

        yield (
            gazetteer_id_for(external_id=external_id),
            external_id,
            row["kind"],
            row["name_en"],
            row["name_ru"] or None,
            _parse_country_codes(external_id=external_id, country_codes=row["country_codes"]),
            _parse_coordinate(row=row, column="latitude", limit=_MAX_LATITUDE),
            _parse_coordinate(row=row, column="longitude", limit=_MAX_LONGITUDE),
            _parse_count(row=row, column="notability"),
        )


def _check_external_id(*, external_id: str) -> None:
    """
    Проверяет, что ключ строки — ключ поставщика с префиксом источника: из него выводится ``id``.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    if not _EXTERNAL_ID.fullmatch(external_id):
        raise InvalidExternalIdError(external_id=external_id)


def _check_country_code(*, external_id: str, country_code: str) -> None:
    """
    Проверяет код страны: колонка из двух символов примет и ``ru``, и ``R1``, и пустую строку.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    if not _COUNTRY_CODE.fullmatch(country_code):
        raise InvalidCountryCodeError(external_id=external_id, country_code=country_code)


def _parse_country_codes(*, external_id: str, country_codes: str) -> list[str]:
    """
    Делит ячейку стран места на коды; пустой код между запятыми и повтор роняют загрузку.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    codes = country_codes.split(_COUNTRY_CODES_SEPARATOR)
    for position, code in enumerate(codes):
        _check_country_code(external_id=external_id, country_code=code)
        if code in codes[:position]:
            raise DuplicateCountryCodeError(external_id=external_id, country_code=code)

    return codes


def _parse_coordinate(*, row: Mapping[str, str], column: str, limit: float) -> float:
    """
    Читает координату в градусах, не дальше ``limit`` от нуля.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    value = row[column]
    try:
        coordinate = float(value)
    except ValueError as error:
        raise InvalidNumberError(external_id=row["external_id"], column=column, value=value) from error

    # Сравнение отсекает и NaN с бесконечностью: float() их разбирает, а колонка REAL принимает.
    if not -limit <= coordinate <= limit:
        raise InvalidNumberError(external_id=row["external_id"], column=column, value=value)

    return coordinate


def _parse_count(*, row: Mapping[str, str], column: str) -> int:
    """
    Читает неотрицательное целое.

    Scenarios:
        - загрузка газеттира в базу: при развёртывании до старта приложения и в дев-стеке
    """
    value = row[column]
    try:
        count = int(value)
    except ValueError as error:
        raise InvalidNumberError(external_id=row["external_id"], column=column, value=value) from error

    if count < 0:
        raise InvalidNumberError(external_id=row["external_id"], column=column, value=value)

    return count
