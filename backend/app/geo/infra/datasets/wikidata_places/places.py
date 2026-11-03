from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from app.geo.domain.enums import PlaceKindEnum
from app.geo.infra.datasets.wikidata.labels import MAX_NAME_LENGTH, acceptable_ru_name, strip_qualifier
from app.shared.types import DictStrAny

_EXTERNAL_ID_PREFIX: Final[str] = "Wikidata:"

# Земная точка — литерал без IRI глобуса впереди: у гор Марса и Луны он начинается с «<http…>».
_EARTH_POINT_PREFIX: Final[str] = "Point("


class ExportOutcomeEnum(StrEnum):
    """Чем кончилась сборка объекта Wikidata: попал в датасет или почему отброшен."""

    KEPT = "kept"
    NO_EARTH_POINT = "no_earth_point"
    NO_COUNTRY = "no_country"
    NO_EN = "no_en"
    NAME_TOO_LONG = "name_too_long"


@dataclass(frozen=True, slots=True)
class ExportedPlace:
    """Место, готовое к записи строкой датасета формата ``places``."""

    external_id: str
    kind: PlaceKindEnum
    name_en: str
    name_ru: str | None
    country_codes: tuple[str, ...]
    latitude: float
    longitude: float
    notability: int


@dataclass(slots=True)
class _PlaceDraft:
    """Всё, что пришло об одном объекте во всех строках ответов, — накапливается при сборке."""

    kind: PlaceKindEnum
    notability: int = 0
    points: set[tuple[float, float]] = field(default_factory=set)
    country_codes: set[str] = field(default_factory=set)
    label_en: str | None = None
    label_ru: str | None = None


def collect_places(
    *,
    class_bindings: Iterable[tuple[PlaceKindEnum, Sequence[DictStrAny]]],
) -> tuple[tuple[ExportedPlace, ...], Counter[tuple[PlaceKindEnum, ExportOutcomeEnum]]]:
    """
    Сводит строки ответов SPARQL в места: одно место на объект Wikidata.

    Объект, уже попавший в более узкий класс, в следующих классах пропускается. Из нескольких
    точек берётся наименьшая по (широта, долгота) — так выбор не зависит от порядка строк.

    Scenarios:
        - сборка новой версии датасета мест из Wikidata

    Args:
        class_bindings: Тип места и строки ответа по его классу — от узкого класса к широкому

    Returns:
        Места, отсортированные по ``external_id``, и итог сборки по типу и исходу
    """
    drafts: dict[str, _PlaceDraft] = {}
    for kind, bindings in class_bindings:
        for binding in bindings:
            qid = binding["item"]["value"].rsplit("/", 1)[-1]
            draft = drafts.setdefault(qid, _PlaceDraft(kind=kind))
            if draft.kind is kind:
                _absorb(draft=draft, binding=binding)

    places: list[ExportedPlace] = []
    outcomes: Counter[tuple[PlaceKindEnum, ExportOutcomeEnum]] = Counter()
    for qid, draft in drafts.items():
        place, outcome = _finish(qid=qid, draft=draft)
        outcomes[draft.kind, outcome] += 1
        if place is not None:
            places.append(place)

    return tuple(sorted(places, key=lambda place: place.external_id)), outcomes


def _absorb(*, draft: _PlaceDraft, binding: DictStrAny) -> None:
    """
    Добавляет в черновик места то, что принесла одна строка ответа.

    Scenarios:
        - сборка новой версии датасета мест из Wikidata
    """
    draft.notability = max(draft.notability, int(binding["links"]["value"]))
    coordinate = binding["coord"]["value"]
    if coordinate.startswith(_EARTH_POINT_PREFIX):
        # WKT: сначала долгота, потом широта.
        longitude, latitude = coordinate.removeprefix(_EARTH_POINT_PREFIX).removesuffix(")").split()
        draft.points.add((float(latitude), float(longitude)))

    if "iso" in binding:
        draft.country_codes.add(binding["iso"]["value"])

    if "en" in binding:
        draft.label_en = binding["en"]["value"]

    if "ru" in binding:
        draft.label_ru = binding["ru"]["value"]


def _finish(*, qid: str, draft: _PlaceDraft) -> tuple[ExportedPlace | None, ExportOutcomeEnum]:
    """
    Проверяет черновик и превращает его в место либо называет причину, по которой он отброшен.

    Scenarios:
        - сборка новой версии датасета мест из Wikidata
    """
    if not draft.points:
        return None, ExportOutcomeEnum.NO_EARTH_POINT

    if not draft.country_codes:
        return None, ExportOutcomeEnum.NO_COUNTRY

    name_en = strip_qualifier(label=draft.label_en or "")
    if not name_en:
        return None, ExportOutcomeEnum.NO_EN

    if len(name_en) > MAX_NAME_LENGTH:
        return None, ExportOutcomeEnum.NAME_TOO_LONG

    latitude, longitude = min(draft.points)
    place = ExportedPlace(
        external_id=f"{_EXTERNAL_ID_PREFIX}{qid}",
        kind=draft.kind,
        name_en=name_en,
        name_ru=None if draft.label_ru is None else acceptable_ru_name(label=draft.label_ru),
        country_codes=tuple(sorted(draft.country_codes)),
        latitude=latitude,
        longitude=longitude,
        notability=draft.notability,
    )
    return place, ExportOutcomeEnum.KEPT
