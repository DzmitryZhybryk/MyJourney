"""Unit-тесты споров русских имён GeoNames и Wikidata и применения решений арбитра."""

from pathlib import Path

import pytest

from app.geo.infra.datasets.exceptions import (
    HumanDecisionOverrideError,
    InvalidRuNameDecisionError,
    UnknownVerdictCityError,
)
from app.geo.infra.datasets.wikidata.disputes import (
    ArbiterVerdict,
    DisputesReport,
    RuNameDecision,
    RuNameDispute,
    apply_decisions,
    find_disputes,
    merge_decisions,
    read_decisions,
    record_verdicts,
    write_decisions,
)
from app.shared.types import DictStrAny

_HUANGSHAN_ROW = {
    "external_id": "GeoNames:1792359",
    "name_en": "Huangshan City",
    "name_ru": "Туньси",
    "country_code": "CN",
    "population": "460786",
}

_HUANGSHAN_DISPUTE = RuNameDispute(
    external_id="GeoNames:1792359",
    name_en="Huangshan City",
    country_code="CN",
    population="460786",
    geonames_ru="Туньси",
    wikidata_ru=frozenset({"Хуаншань"}),
)

_HUANGSHAN_DECISION = RuNameDecision(
    external_id="GeoNames:1792359",
    geonames_ru="Туньси",
    wikidata_ru=frozenset({"Хуаншань"}),
    name_ru="Хуаншань",
    decided_by="llm",
    reason="Tunxi is the central district",
)


def test_find_disputes_reports_different_names() -> None:
    """find_disputes: имя GeoNames и метка Wikidata разные → спор с обоими вариантами."""
    disputes = find_disputes(rows=[_HUANGSHAN_ROW], labels={"1792359": frozenset({"Хуаншань"})})

    assert disputes == (_HUANGSHAN_DISPUTE,)


@pytest.mark.parametrize(
    "label",
    ["Туньси", "туньси", "Туньси (город)"],
    ids=["same", "case", "qualifier"],
)
def test_find_disputes_ignores_same_name(label: str) -> None:
    """find_disputes: совпадение с точностью до регистра и уточнения в скобках — не спор."""
    assert find_disputes(rows=[_HUANGSHAN_ROW], labels={"1792359": frozenset({label})}) == ()


@pytest.mark.parametrize(
    ("geonames_ru", "label"),
    [("Гёйчай", "Гейчай"), ("Самдруп-Джонгхар", "Самдруп Джонгхар")],
    ids=["yo", "hyphen"],
)
def test_find_disputes_ignores_yo_and_hyphen_differences(geonames_ru: str, label: str) -> None:
    """find_disputes: «ё»/«е» и дефис вместо пробела — то же имя, не спор."""
    row = {**_HUANGSHAN_ROW, "name_ru": geonames_ru}

    assert find_disputes(rows=[row], labels={"1792359": frozenset({label})}) == ()


@pytest.mark.parametrize(
    ("row", "labels"),
    [
        ({**_HUANGSHAN_ROW, "name_ru": ""}, {"1792359": frozenset({"Хуаншань"})}),
        ({**_HUANGSHAN_ROW, "external_id": "OSM:1"}, {"1792359": frozenset({"Хуаншань"})}),
        (_HUANGSHAN_ROW, {}),
        (_HUANGSHAN_ROW, {"1792359": frozenset({"Huangshan"})}),
    ],
    ids=["no-geonames-name", "not-geonames", "no-wikidata-label", "only-unacceptable-label"],
)
def test_find_disputes_needs_both_names(row: dict[str, str], labels: dict[str, frozenset[str]]) -> None:
    """find_disputes: спор только когда есть и имя GeoNames, и годная метка Wikidata."""
    assert find_disputes(rows=[row], labels=labels) == ()


def test_apply_decisions_uses_current_decision() -> None:
    """apply_decisions: решение записано для тех же имён → имя из решения, спор решён."""
    decision = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Туньси",
        wikidata_ru=frozenset({"Хуаншань"}),
        name_ru="Хуаншань",
        decided_by="llm",
        reason="Tunxi is the central district",
    )

    rows, unresolved, report = apply_decisions(
        rows=[_HUANGSHAN_ROW],
        disputes=[_HUANGSHAN_DISPUTE],
        decisions={decision.external_id: decision},
    )

    assert rows[0]["name_ru"] == "Хуаншань"
    assert unresolved == ()
    assert report == DisputesReport(disputes=1, resolved=1, unresolved=0, corrected=0, stale=0)


@pytest.mark.parametrize(
    ("geonames_ru", "wikidata_ru"),
    [("Тунси", frozenset({"Хуаншань"})), ("Туньси", frozenset({"Хуаншаньши"}))],
    ids=["geonames-changed", "wikidata-changed"],
)
def test_apply_decisions_ignores_stale_decision(geonames_ru: str, wikidata_ru: frozenset[str]) -> None:
    """apply_decisions: решение записано для других имён → устарело, имя GeoNames, спор не решён."""
    decision = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru=geonames_ru,
        wikidata_ru=wikidata_ru,
        name_ru="Хуаншань",
        decided_by="llm",
        reason="stale",
    )

    rows, unresolved, report = apply_decisions(
        rows=[_HUANGSHAN_ROW],
        disputes=[_HUANGSHAN_DISPUTE],
        decisions={decision.external_id: decision},
    )

    assert rows[0]["name_ru"] == "Туньси"
    assert unresolved == (_HUANGSHAN_DISPUTE,)
    assert report == DisputesReport(disputes=1, resolved=0, unresolved=1, corrected=0, stale=0)


def test_apply_decisions_without_decision_keeps_geonames_name() -> None:
    """apply_decisions: решения нет → имя GeoNames, спор уходит на арбитраж."""
    rows, unresolved, _ = apply_decisions(rows=[_HUANGSHAN_ROW], disputes=[_HUANGSHAN_DISPUTE], decisions={})

    assert rows[0]["name_ru"] == "Туньси"
    assert unresolved == (_HUANGSHAN_DISPUTE,)


def test_apply_decisions_corrects_broken_name_without_dispute() -> None:
    """apply_decisions: решение без меток Wikidata правит сломанное имя GeoNames, спора по городу нет."""
    row = {**_HUANGSHAN_ROW, "external_id": "GeoNames:2112297", "name_en": "Kamogawa", "name_ru": "Камогаwа"}
    decision = RuNameDecision(
        external_id="GeoNames:2112297",
        geonames_ru="Камогаwа",
        wikidata_ru=frozenset(),
        name_ru="Камогава",
        decided_by="llm",
        reason="Latin letter inside Cyrillic",
    )

    rows, unresolved, report = apply_decisions(rows=[row], disputes=[], decisions={decision.external_id: decision})

    assert rows[0]["name_ru"] == "Камогава"
    assert unresolved == ()
    assert report == DisputesReport(disputes=0, resolved=0, unresolved=0, corrected=1, stale=0)


@pytest.mark.parametrize(
    ("name_ru", "disputes"),
    [("Камогава-си", []), ("Камогаwа", [_HUANGSHAN_DISPUTE])],
    ids=["geonames-changed", "now-disputed"],
)
def test_apply_decisions_skips_correction_that_no_longer_fits(name_ru: str, disputes: list[RuNameDispute]) -> None:
    """apply_decisions: правка без спора не действует, если имя GeoNames сменилось или по городу появился спор."""
    row = {**_HUANGSHAN_ROW, "name_ru": name_ru}
    decision = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Камогаwа",
        wikidata_ru=frozenset(),
        name_ru="Камогава",
        decided_by="llm",
        reason="Latin letter inside Cyrillic",
    )

    rows, _, report = apply_decisions(rows=[row], disputes=disputes, decisions={decision.external_id: decision})

    assert rows[0]["name_ru"] == name_ru
    assert report.corrected == 0


@pytest.mark.parametrize(
    "name_ru",
    ["Туньси", "Тунси", ""],
    ids=["label-gone", "geonames-changed", "geonames-name-gone"],
)
def test_apply_decisions_sends_stale_decision_without_dispute_to_arbitration(name_ru: str) -> None:
    """apply_decisions: спора по городу решения больше нет, а имени из решения в строке нет → решение устарело."""
    row = {**_HUANGSHAN_ROW, "name_ru": name_ru}

    rows, unresolved, report = apply_decisions(
        rows=[row],
        disputes=[],
        decisions={_HUANGSHAN_DECISION.external_id: _HUANGSHAN_DECISION},
    )

    assert rows[0]["name_ru"] == name_ru
    assert unresolved == (
        RuNameDispute(
            external_id="GeoNames:1792359",
            name_en="Huangshan City",
            country_code="CN",
            population="460786",
            geonames_ru=name_ru,
            wikidata_ru=frozenset(),
        ),
    )
    assert report == DisputesReport(disputes=0, resolved=0, unresolved=0, corrected=0, stale=1)


def test_apply_decisions_reports_stale_correction() -> None:
    """apply_decisions: имя GeoNames сменилось после правки без спора → правка устарела и уходит на арбитраж."""
    row = {**_HUANGSHAN_ROW, "name_ru": "Камогава-си"}
    decision = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Камогаwа",
        wikidata_ru=frozenset(),
        name_ru="Камогава",
        decided_by="llm",
        reason="Latin letter inside Cyrillic",
    )

    _, unresolved, report = apply_decisions(rows=[row], disputes=[], decisions={decision.external_id: decision})

    assert [dispute.geonames_ru for dispute in unresolved] == ["Камогава-си"]
    assert report.stale == 1


def test_apply_decisions_accepts_already_applied_decision_without_dispute() -> None:
    """apply_decisions: на входе версия с применённым решением, спора нет → имя то же, решение не устарело."""
    row = {**_HUANGSHAN_ROW, "name_ru": "Хуаншань"}

    rows, unresolved, report = apply_decisions(
        rows=[row],
        disputes=[],
        decisions={_HUANGSHAN_DECISION.external_id: _HUANGSHAN_DECISION},
    )

    assert rows[0]["name_ru"] == "Хуаншань"
    assert unresolved == ()
    assert report == DisputesReport(disputes=0, resolved=0, unresolved=0, corrected=0, stale=0)


def test_apply_decisions_accepts_already_applied_third_name() -> None:
    """apply_decisions: в строке уже третье имя из решения, метки Wikidata те же → спор решён, а не устарел."""
    decision = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Туньси",
        wikidata_ru=frozenset({"Хуаншаньши"}),
        name_ru="Хуаншань",
        decided_by="llm",
        reason="neither label is the city name",
    )
    row = {**_HUANGSHAN_ROW, "name_ru": "Хуаншань"}
    dispute = RuNameDispute(
        external_id="GeoNames:1792359",
        name_en="Huangshan City",
        country_code="CN",
        population="460786",
        geonames_ru="Хуаншань",
        wikidata_ru=frozenset({"Хуаншаньши"}),
    )

    rows, unresolved, report = apply_decisions(
        rows=[row],
        disputes=[dispute],
        decisions={decision.external_id: decision},
    )

    assert rows[0]["name_ru"] == "Хуаншань"
    assert unresolved == ()
    assert report == DisputesReport(disputes=1, resolved=1, unresolved=0, corrected=0, stale=0)


def test_record_verdicts_captures_disputed_names() -> None:
    """record_verdicts: вердикт по спору запоминает оба спорящих имени — для проверки актуальности."""
    verdict = ArbiterVerdict(
        external_id="GeoNames:1792359",
        name_ru="Хуаншань",
        decided_by="llm",
        reason="Tunxi is the central district",
    )

    [decision] = record_verdicts(verdicts=[verdict], rows=[_HUANGSHAN_ROW], disputes=[_HUANGSHAN_DISPUTE])

    assert decision == RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Туньси",
        wikidata_ru=frozenset({"Хуаншань"}),
        name_ru="Хуаншань",
        decided_by="llm",
        reason="Tunxi is the central district",
    )


def test_record_verdicts_without_dispute_is_correction() -> None:
    """record_verdicts: вердикт по городу без спора — правка имени GeoNames с пустыми метками Wikidata."""
    row = {**_HUANGSHAN_ROW, "external_id": "GeoNames:2112297", "name_ru": "Камогаwа"}
    verdict = ArbiterVerdict(external_id="GeoNames:2112297", name_ru="Камогава", decided_by="human", reason="typo")

    [decision] = record_verdicts(verdicts=[verdict], rows=[row], disputes=[])

    assert decision.geonames_ru == "Камогаwа"
    assert decision.wikidata_ru == frozenset()


def test_record_verdicts_unknown_city_raises() -> None:
    """record_verdicts: вердикт по городу, которого нет в датасете, — ошибка, а не молчаливый пропуск."""
    verdict = ArbiterVerdict(external_id="GeoNames:404", name_ru="Нигде", decided_by="llm", reason="-")

    with pytest.raises(UnknownVerdictCityError, match="GeoNames:404"):
        record_verdicts(verdicts=[verdict], rows=[_HUANGSHAN_ROW], disputes=[])


def test_decisions_file_roundtrip(tmp_path: Path) -> None:
    """write_decisions → read_decisions: решения переживают файл, несколько меток Wikidata — тоже."""
    path = tmp_path / "decisions.csv"
    decisions = [
        RuNameDecision(
            external_id="GeoNames:2",
            geonames_ru="Сёдермальм",
            wikidata_ru=frozenset({"Стокгольм", "Сёдермальм район"}),
            name_ru="Сёдермальм",
            decided_by="human",
            reason="district, not the city",
        ),
        RuNameDecision(
            external_id="GeoNames:1",
            geonames_ru="Туньси",
            wikidata_ru=frozenset({"Хуаншань"}),
            name_ru="Хуаншань",
            decided_by="llm",
            reason="Tunxi is the central district",
        ),
        RuNameDecision(
            external_id="GeoNames:3",
            geonames_ru="Камогаwа",
            wikidata_ru=frozenset(),
            name_ru="Камогава",
            decided_by="llm",
            reason="Latin letter inside Cyrillic",
        ),
    ]

    write_decisions(decisions=decisions, path=path)

    assert read_decisions(path=path) == {decision.external_id: decision for decision in decisions}
    assert [line.split(",")[0] for line in path.read_text(encoding="utf-8").splitlines()[1:]] == [
        "GeoNames:1",
        "GeoNames:2",
        "GeoNames:3",
    ]


@pytest.mark.parametrize(
    ("entry", "match"),
    [
        ({"name_ru": ""}, "name_ru ''"),
        ({"name_ru": None}, "name_ru None"),
        ({"name_ru": "  "}, "name_ru '  '"),
        ({"name_ru": " Хуаншань"}, "name_ru ' Хуаншань'"),
        ({"decided_by": "gpt"}, "decided_by 'gpt'"),
    ],
    ids=["empty-name", "null-name", "blank-name", "padded-name", "unknown-decider"],
)
def test_record_verdicts_rejects_invalid_verdict(entry: DictStrAny, match: str) -> None:
    """record_verdicts: вердикт без имени или с неизвестным автором — ошибка, а не стёртое имя города."""
    verdict_entry: DictStrAny = {
        "external_id": "GeoNames:1792359",
        "name_ru": "Хуаншань",
        "decided_by": "llm",
        "reason": "-",
    }
    verdict = ArbiterVerdict(**(verdict_entry | entry))

    with pytest.raises(InvalidRuNameDecisionError, match=match):
        record_verdicts(verdicts=[verdict], rows=[_HUANGSHAN_ROW], disputes=[_HUANGSHAN_DISPUTE])


def test_record_verdicts_rejects_duplicate_city() -> None:
    """record_verdicts: два вердикта по одному городу — ошибка, а не молчаливая победа второго."""
    verdict = ArbiterVerdict(external_id="GeoNames:1792359", name_ru="Хуаншань", decided_by="llm", reason="-")

    with pytest.raises(InvalidRuNameDecisionError, match="duplicate"):
        record_verdicts(verdicts=[verdict, verdict], rows=[_HUANGSHAN_ROW], disputes=[_HUANGSHAN_DISPUTE])


@pytest.mark.parametrize(
    ("lines", "match"),
    [
        (
            [
                "GeoNames:1,Туньси,Хуаншань,Хуаншань,human,district",
                "GeoNames:1,Туньси,Хуаншань,Туньси,llm,again",
            ],
            "duplicate",
        ),
        (["GeoNames:1,Туньси,Хуаншань,,llm,unsure"], "name_ru ''"),
        (["GeoNames:1,Туньси,Хуаншань,Хуаншань,editor,-"], "decided_by 'editor'"),
    ],
    ids=["duplicate-city", "empty-name", "unknown-decider"],
)
def test_read_decisions_rejects_invalid_file(tmp_path: Path, lines: list[str], match: str) -> None:
    """read_decisions: файл правится руками, поэтому повтор города, пустое имя и чужой автор — ошибка чтения."""
    path = tmp_path / "decisions.csv"
    path.write_text("\n".join(["external_id,geonames_ru,wikidata_ru,name_ru,decided_by,reason", *lines]) + "\n")

    with pytest.raises(InvalidRuNameDecisionError, match=match):
        read_decisions(path=path)


def test_merge_decisions_replaces_decision_by_city() -> None:
    """merge_decisions: новое решение по городу заменяет прежнее, остальные решения остаются."""
    other = RuNameDecision(
        external_id="GeoNames:2",
        geonames_ru="Камогаwа",
        wikidata_ru=frozenset(),
        name_ru="Камогава",
        decided_by="llm",
        reason="typo",
    )
    recorded = RuNameDecision(
        external_id="GeoNames:1792359",
        geonames_ru="Туньси",
        wikidata_ru=frozenset({"Хуаншань"}),
        name_ru="Туньси",
        decided_by="llm",
        reason="re-arbitrated",
    )

    merged = merge_decisions(
        decisions={_HUANGSHAN_DECISION.external_id: _HUANGSHAN_DECISION, other.external_id: other},
        recorded=[recorded],
    )

    assert merged == {recorded.external_id: recorded, other.external_id: other}


def test_merge_decisions_llm_cannot_override_human_decision() -> None:
    """merge_decisions: вердикт LLM по городу с решением человека — ошибка, решение человека не затирается."""
    human_decision = RuNameDecision(
        external_id="GeoNames:611403",
        geonames_ru="Цхинвал",
        wikidata_ru=frozenset({"Цхинвали"}),
        name_ru="Цхинвали",
        decided_by="human",
        reason="owner's choice",
    )
    recorded = RuNameDecision(
        external_id="GeoNames:611403",
        geonames_ru="Цхинвал",
        wikidata_ru=frozenset({"Цхинвали"}),
        name_ru="Цхинвал",
        decided_by="llm",
        reason="re-arbitrated",
    )

    with pytest.raises(HumanDecisionOverrideError, match="GeoNames:611403"):
        merge_decisions(decisions={"GeoNames:611403": human_decision}, recorded=[recorded])


def test_merge_decisions_human_overrides_human_decision() -> None:
    """merge_decisions: решение человека меняет только новое решение человека."""
    human_decision = RuNameDecision(
        external_id="GeoNames:611403",
        geonames_ru="Цхинвал",
        wikidata_ru=frozenset({"Цхинвали"}),
        name_ru="Цхинвали",
        decided_by="human",
        reason="owner's choice",
    )
    recorded = RuNameDecision(
        external_id="GeoNames:611403",
        geonames_ru="Цхинвал",
        wikidata_ru=frozenset({"Цхинвали"}),
        name_ru="Цхинвал",
        decided_by="human",
        reason="owner changed their mind",
    )

    merged = merge_decisions(decisions={"GeoNames:611403": human_decision}, recorded=[recorded])

    assert merged == {"GeoNames:611403": recorded}
