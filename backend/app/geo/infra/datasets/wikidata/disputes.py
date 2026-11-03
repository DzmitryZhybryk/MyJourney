import csv
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.geo.infra.datasets.exceptions import (
    HumanDecisionOverrideError,
    InvalidRuNameDecisionError,
    UnknownVerdictCityError,
)
from app.geo.infra.datasets.wikidata.labels import acceptable_ru_names, geonames_id_of

DECISIONS_PATH: Final[Path] = Path(__file__).parents[1] / "ru_name_decisions.csv"

DECISION_COLUMNS: Final[tuple[str, ...]] = (
    "external_id",
    "geonames_ru",
    "wikidata_ru",
    "name_ru",
    "decided_by",
    "reason",
)

# Несколько меток Wikidata в одной ячейке файла решений.
_LABELS_SEPARATOR: Final[str] = " | "

_SPACES_AND_DASHES: Final[re.Pattern[str]] = re.compile(r"[\s\-‐–—]+")

_HUMAN: Final[str] = "human"
_DECIDERS: Final[frozenset[str]] = frozenset({"llm", _HUMAN})


@dataclass(frozen=True, slots=True)
class RuNameDispute:
    """Город, у которого русское имя GeoNames расходится с меткой Wikidata."""

    external_id: str
    name_en: str
    country_code: str
    population: str
    geonames_ru: str
    wikidata_ru: frozenset[str]


@dataclass(frozen=True, slots=True)
class RuNameDecision:
    """Решение арбитра по спору: какое русское имя показывать и почему."""

    external_id: str
    geonames_ru: str
    wikidata_ru: frozenset[str]
    name_ru: str
    decided_by: str
    reason: str


@dataclass(frozen=True, slots=True)
class DisputesReport:
    """
    Итог применения решений.

    Сколько споров нашлось и сколько из них решено, сколько имён исправлено без спора и сколько
    решений устарело у городов, по которым спора больше нет.
    """

    disputes: int
    resolved: int
    unresolved: int
    corrected: int
    stale: int


def find_disputes(
    *,
    rows: Iterable[Mapping[str, str]],
    labels: Mapping[str, frozenset[str]],
) -> tuple[RuNameDispute, ...]:
    """
    Находит города, где русское имя GeoNames и метка Wikidata расходятся по существу.

    Различия только в «ё»/«е», дефисах, пробелах и регистре спором не считаются.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - выгрузка споров о русских названиях на арбитраж

    Args:
        rows: Строки файла датасета
        labels: Метки Wikidata по id GeoNames

    Returns:
        Споры в порядке строк
    """
    disputes: list[RuNameDispute] = []
    for row in rows:
        geonames_id = geonames_id_of(external_id=row["external_id"])
        if not row["name_ru"] or geonames_id is None:
            continue

        names = acceptable_ru_names(labels=labels.get(geonames_id, frozenset()))
        if not names or any(_same_name(left=row["name_ru"], right=name) for name in names):
            continue

        disputes.append(
            RuNameDispute(
                external_id=row["external_id"],
                name_en=row["name_en"],
                country_code=row["country_code"],
                population=row["population"],
                geonames_ru=row["name_ru"],
                wikidata_ru=names,
            ),
        )

    return tuple(disputes)


def apply_decisions(
    *,
    rows: Iterable[Mapping[str, str]],
    disputes: Iterable[RuNameDispute],
    decisions: Mapping[str, RuNameDecision],
) -> tuple[tuple[dict[str, str], ...], tuple[RuNameDispute, ...], DisputesReport]:
    """
    Подставляет имена по решениям арбитра; спор без актуального решения сохраняет имя GeoNames.

    Решение актуально, только если записано для тех же имён, что спорят сейчас: изменилось имя в
    GeoNames или метки Wikidata — решение устарело, и спор уходит на повторный арбитраж. Решение
    без меток Wikidata — ручная правка сломанного имени GeoNames, у которого спорить не с чем: оно
    действует, пока в GeoNames то же имя и спора по городу нет.

    На входе может быть и версия датасета, уже собранная с этими решениями: имя из решения в строке
    значит, что решение применено. Решение по городу, где спора нет, а в строке другое имя, устарело —
    город уходит на арбитраж без меток Wikidata.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata
        - выгрузка споров о русских названиях на арбитраж: споры без актуального решения

    Args:
        rows: Строки файла датасета
        disputes: Споры этих строк (см. ``find_disputes``)
        decisions: Решения по ``external_id``

    Returns:
        Строки в исходном порядке, города для повторного арбитража (споры без актуального решения,
        затем устаревшие решения) и итог
    """
    names_by_id: dict[str, str] = {}
    unresolved: list[RuNameDispute] = []
    disputed_ids: set[str] = set()
    for dispute in disputes:
        disputed_ids.add(dispute.external_id)
        decision = decisions.get(dispute.external_id)
        if decision is not None and _decides(decision=decision, dispute=dispute):
            names_by_id[dispute.external_id] = decision.name_ru
        else:
            unresolved.append(dispute)

    resolved = len(names_by_id)
    unresolved_disputes = len(unresolved)
    result: list[dict[str, str]] = []
    for row in rows:
        new_row = dict(row)
        external_id = row["external_id"]
        decision = decisions.get(external_id)
        if external_id not in disputed_ids and decision is not None and decision.name_ru != row["name_ru"]:
            if not decision.wikidata_ru and decision.geonames_ru == row["name_ru"]:
                names_by_id[external_id] = decision.name_ru
            else:
                unresolved.append(_stale_decision_dispute(row=row))

        name = names_by_id.get(external_id)
        if name is not None:
            new_row["name_ru"] = name

        result.append(new_row)

    report = DisputesReport(
        disputes=len(disputed_ids),
        resolved=resolved,
        unresolved=unresolved_disputes,
        corrected=len(names_by_id) - resolved,
        stale=len(unresolved) - unresolved_disputes,
    )
    return tuple(result), tuple(unresolved), report


def merge_decisions(
    *,
    decisions: Mapping[str, RuNameDecision],
    recorded: Iterable[RuNameDecision],
) -> dict[str, RuNameDecision]:
    """
    Дописывает новые решения к файлу решений; решение по тому же городу заменяет прежнее.

    Scenarios:
        - запись вердиктов арбитра в файл решений

    Args:
        decisions: Решения из файла по ``external_id``
        recorded: Новые решения (см. ``record_verdicts``)

    Returns:
        Все решения по ``external_id``

    Raises:
        HumanDecisionOverrideError: новое решение не от человека заменяет решение человека
    """
    merged = dict(decisions)
    for decision in recorded:
        current = merged.get(decision.external_id)
        if current is not None and current.decided_by == _HUMAN and decision.decided_by != _HUMAN:
            raise HumanDecisionOverrideError(external_id=decision.external_id)

        merged[decision.external_id] = decision

    return merged


@dataclass(frozen=True, slots=True)
class ArbiterVerdict:
    """Вердикт арбитра по городу: какое русское имя показывать, кто решил и почему."""

    external_id: str
    name_ru: str
    decided_by: str
    reason: str


def record_verdicts(
    *,
    verdicts: Iterable[ArbiterVerdict],
    rows: Iterable[Mapping[str, str]],
    disputes: Iterable[RuNameDispute],
) -> tuple[RuNameDecision, ...]:
    """
    Превращает вердикты арбитра в решения, фиксируя имена, о которых шла речь.

    Для города в споре решение запоминает оба спорящих имени; для города без спора — правка
    сломанного имени GeoNames — только его, с пустыми метками Wikidata.

    Scenarios:
        - запись вердиктов арбитра в файл решений

    Args:
        verdicts: Вердикты арбитра
        rows: Строки файла датасета
        disputes: Текущие споры этих строк

    Returns:
        Решения в порядке вердиктов

    Raises:
        UnknownVerdictCityError: вердикт ссылается на город, которого нет в датасете
        InvalidRuNameDecisionError: вердикт без имени, с неизвестным автором или повторный по городу
    """
    disputes_by_id = {dispute.external_id: dispute for dispute in disputes}
    names_by_id = {row["external_id"]: row["name_ru"] for row in rows}
    decisions: list[RuNameDecision] = []
    seen_ids: set[str] = set()
    for verdict in verdicts:
        _check_decision(
            external_id=verdict.external_id,
            name_ru=verdict.name_ru,
            decided_by=verdict.decided_by,
            seen_ids=seen_ids,
        )
        seen_ids.add(verdict.external_id)
        dispute = disputes_by_id.get(verdict.external_id)
        if dispute is not None:
            geonames_ru, wikidata_ru = dispute.geonames_ru, dispute.wikidata_ru
        elif verdict.external_id in names_by_id:
            geonames_ru, wikidata_ru = names_by_id[verdict.external_id], frozenset[str]()
        else:
            raise UnknownVerdictCityError(external_id=verdict.external_id)

        decisions.append(
            RuNameDecision(
                external_id=verdict.external_id,
                geonames_ru=geonames_ru,
                wikidata_ru=wikidata_ru,
                name_ru=verdict.name_ru,
                decided_by=verdict.decided_by,
                reason=verdict.reason,
            ),
        )

    return tuple(decisions)


def read_decisions(*, path: Path = DECISIONS_PATH) -> dict[str, RuNameDecision]:
    """
    Читает файл решений арбитра.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: применение решений
        - запись вердиктов арбитра в файл решений

    Args:
        path: Путь к CSV (по умолчанию — ``ru_name_decisions.csv`` рядом с манифестом)

    Returns:
        Решения по ``external_id``

    Raises:
        InvalidRuNameDecisionError: строка без имени, с неизвестным автором или повторный город
    """
    decisions: dict[str, RuNameDecision] = {}
    with path.open(encoding="utf-8", newline="") as decisions_file:
        for row in csv.DictReader(decisions_file):
            _check_decision(
                external_id=row["external_id"],
                name_ru=row["name_ru"],
                decided_by=row["decided_by"],
                seen_ids=decisions.keys(),
            )
            decisions[row["external_id"]] = RuNameDecision(
                external_id=row["external_id"],
                geonames_ru=row["geonames_ru"],
                wikidata_ru=frozenset(row["wikidata_ru"].split(_LABELS_SEPARATOR))
                if row["wikidata_ru"]
                else frozenset(),
                name_ru=row["name_ru"],
                decided_by=row["decided_by"],
                reason=row["reason"],
            )

    return decisions


def write_decisions(*, decisions: Iterable[RuNameDecision], path: Path = DECISIONS_PATH) -> None:
    """
    Пишет файл решений арбитра, отсортированный по ``external_id`` — чтобы дифф показывал только правки.

    Scenarios:
        - запись вердиктов арбитра в файл решений

    Args:
        decisions: Решения
        path: Путь к CSV
    """
    with path.open("w", encoding="utf-8", newline="") as decisions_file:
        writer = csv.DictWriter(decisions_file, fieldnames=DECISION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for decision in sorted(decisions, key=lambda item: item.external_id):
            writer.writerow(
                {
                    "external_id": decision.external_id,
                    "geonames_ru": decision.geonames_ru,
                    "wikidata_ru": _LABELS_SEPARATOR.join(sorted(decision.wikidata_ru)),
                    "name_ru": decision.name_ru,
                    "decided_by": decision.decided_by,
                    "reason": decision.reason,
                },
            )


def _decides(*, decision: RuNameDecision, dispute: RuNameDispute) -> bool:
    """
    Решает ли решение этот спор: те же метки Wikidata, а в строке имя GeoNames или уже имя из решения.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: применение решений
    """
    return decision.wikidata_ru == dispute.wikidata_ru and dispute.geonames_ru in {
        decision.geonames_ru,
        decision.name_ru,
    }


def _stale_decision_dispute(*, row: Mapping[str, str]) -> RuNameDispute:
    """
    Город устаревшего решения для повторного арбитража; метки Wikidata не передаются.

    Scenarios:
        - выгрузка споров о русских названиях на арбитраж: устаревшие решения
    """
    return RuNameDispute(
        external_id=row["external_id"],
        name_en=row["name_en"],
        country_code=row["country_code"],
        population=row["population"],
        geonames_ru=row["name_ru"],
        wikidata_ru=frozenset(),
    )


def _check_decision(*, external_id: str, name_ru: str, decided_by: str, seen_ids: Collection[str]) -> None:
    """
    Отсекает решение, которое нельзя применять.

    Пустое имя или ``null`` в вердикте — это «не знаю», а не имя: применённое, оно стёрло бы название
    города. Пробелы по краям и неизвестный автор — признаки сломанной записи. Второе решение по тому же
    городу молча затёрло бы первое.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: чтение файла решений
        - запись вердиктов арбитра в файл решений

    Raises:
        InvalidRuNameDecisionError: решение не проходит проверку
    """
    if not name_ru or name_ru != name_ru.strip():
        raise InvalidRuNameDecisionError(external_id=external_id, problem=f"name_ru {name_ru!r}")

    if decided_by not in _DECIDERS:
        raise InvalidRuNameDecisionError(external_id=external_id, problem=f"decided_by {decided_by!r}")

    if external_id in seen_ids:
        raise InvalidRuNameDecisionError(external_id=external_id, problem="duplicate decision")


def _same_name(*, left: str, right: str) -> bool:
    """
    Одно ли это имя с точностью до «ё»/«е», дефисов, пробелов и регистра.

    Scenarios:
        - сборка новой версии датасета с русскими названиями из Wikidata: поиск споров
    """
    return _normalize(name=left) == _normalize(name=right)


def _normalize(*, name: str) -> str:
    return _SPACES_AND_DASHES.sub(" ", name.replace("ё", "е").replace("Ё", "Е")).strip().lower()
