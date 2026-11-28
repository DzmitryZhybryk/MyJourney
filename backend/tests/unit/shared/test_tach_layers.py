"""
Guard: каждая связь в ``tach.toml`` идёт по слоям и между доменами только по принятым образцам.

tach проверяет код по объявленным связям, но сами связи пишутся руками: связь, добавленная ради
удобства (``application`` → чужой домен), прошла бы tach вместе с кодом. Здесь разрешённые формы
связей записаны таблицами, и каждая связь из ``tach.toml`` сверяется с ними.
"""

import tomllib
from pathlib import Path
from typing import Final

import pytest

# tests/unit/shared/<этот файл> → backend/
_TACH_TOML: Final[Path] = Path(__file__).resolve().parents[3] / "tach.toml"
_SHARED: Final[str] = "app.shared"
_DEVTOOLS: Final[str] = "devtools"

_OWN_DOMAIN_TARGETS: Final[dict[str, frozenset[str]]] = {
    "exceptions": frozenset(),
    "domain": frozenset({"exceptions"}),
    "application": frozenset({"domain", "exceptions"}),
    "infra": frozenset({"domain", "application", "exceptions"}),
    "presentation": frozenset({"domain", "application", "infra", "exceptions"}),
    "scripts": frozenset({"domain", "application", "infra", "exceptions"}),
}
_FOREIGN_DOMAIN_TARGETS: Final[dict[str, frozenset[str]]] = {
    "infra": frozenset({"application"}),
    "presentation": frozenset({"application", "presentation"}),
}
_DEVTOOLS_TARGETS: Final[frozenset[str]] = frozenset({"domain", "infra"})


def _tach_edges() -> tuple[tuple[str, str], ...]:
    tach_config = tomllib.loads(_TACH_TOML.read_text(encoding="utf-8"))
    return tuple(
        (module["path"], target) for module in tach_config["modules"] for target in module.get("depends_on", ())
    )


def _split_domain_layer(module_path: str) -> tuple[str, str]:
    app_prefix, domain, layer = module_path.split(".")
    assert app_prefix == "app", f"не модуль домена: {module_path}"
    return domain, layer


def _is_allowed(*, source: str, target: str) -> bool:
    if source == _SHARED:
        return False

    if target == _SHARED:
        return True

    target_domain, target_layer = _split_domain_layer(target)
    if source == _DEVTOOLS:
        return target_layer in _DEVTOOLS_TARGETS

    source_domain, source_layer = _split_domain_layer(source)
    if source_domain == target_domain:
        return target_layer in _OWN_DOMAIN_TARGETS[source_layer]

    return target_layer in _FOREIGN_DOMAIN_TARGETS.get(source_layer, frozenset())


@pytest.mark.parametrize(("source", "target"), _tach_edges())
def test_tach_edge_declared_in_toml_follows_layer_rules(source: str, target: str) -> None:
    """Каждая связь из tach.toml разрешена правилами слоёв и связей между доменами."""
    assert _is_allowed(source=source, target=target), f"{source} → {target} нарушает правила слоёв"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("app.media.application", "app.users.application"),
        ("app.media.domain", "app.media.application"),
        ("app.media.application", "app.media.infra"),
        ("app.media.infra", "app.users.infra"),
        ("app.journeys.infra", "app.geo.presentation"),
        ("app.shared", "app.media.domain"),
        ("devtools", "app.geo.presentation"),
    ],
)
def test_tach_edge_breaking_layer_rules_is_rejected(source: str, target: str) -> None:
    """Связь против направления слоёв или в чужой домен не по образцу проверка отвергает."""
    assert not _is_allowed(source=source, target=target)
