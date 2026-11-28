"""
Unit-тесты ``run_components`` — общего жизненного цикла компонентов API-процесса и воркера.

Порядок старта и остановки виден по общему журналу ``FakeComponent``; ошибки старта, тела и
остановки проверяются на том, что поднятое всё равно закрывается, а наружу летит нужная ошибка.
"""

import pytest
from structlog.testing import capture_logs

from app.shared.infra.di.lifecycle import run_components
from app.shared.infra.di.registry import ComponentRegistry
from tests.fakes import FakeComponent


async def test_run_components_starts_in_order_and_stops_in_reverse() -> None:
    """Старт — в порядке списка, с переданным реестром; остановка — в обратном, после выхода из тела."""
    events: list[str] = []
    registry = ComponentRegistry()
    first = FakeComponent(name="first", events=events)
    second = FakeComponent(name="second", events=events)

    async with run_components(components=[first, second], registry=registry):
        events.append("body")

    assert events == ["start:first", "start:second", "body", "stop:second", "stop:first"]
    assert first.registry is registry
    assert second.registry is registry


async def test_run_components_failed_startup_stops_started_and_reraises() -> None:
    """Упал старт второго: первый остановлен, третий не стартовал, тело не выполнялось, ошибка старта наружу."""
    events: list[str] = []
    components = [
        FakeComponent(name="first", events=events),
        FakeComponent(name="second", events=events, startup_error=RuntimeError("db unreachable")),
        FakeComponent(name="third", events=events),
    ]

    with pytest.raises(RuntimeError, match="db unreachable"):
        async with run_components(components=components, registry=ComponentRegistry()):
            events.append("body")

    assert events == ["start:first", "stop:first"]


async def test_run_components_failed_startup_logs_component_with_traceback() -> None:
    """Сбой старта пишется в лог ошибкой с именем компонента и трейсбеком — трейсбек сам компонент не называет."""
    components = [FakeComponent(name="broken", events=[], startup_error=RuntimeError("db unreachable"))]

    with capture_logs() as logs, pytest.raises(RuntimeError, match="db unreachable"):
        async with run_components(components=components, registry=ComponentRegistry()):
            pass

    assert logs == [
        {
            "event": "component.startup_failed",
            "component": "FakeComponent",
            "log_level": "error",
            "exc_info": True,
        }
    ]


async def test_run_components_failed_shutdown_stops_the_rest_and_reraises_first() -> None:
    """Остановка двух компонентов падает: средний всё равно остановлен, наружу — первая по порядку остановки ошибка."""
    events: list[str] = []
    first_error = RuntimeError("first stop failed")
    third_error = RuntimeError("third stop failed")
    components = [
        FakeComponent(name="first", events=events, shutdown_error=first_error),
        FakeComponent(name="second", events=events),
        FakeComponent(name="third", events=events, shutdown_error=third_error),
    ]

    with capture_logs() as logs, pytest.raises(RuntimeError) as exc_info:
        async with run_components(components=components, registry=ComponentRegistry()):
            pass

    assert exc_info.value is third_error
    assert events == ["start:first", "start:second", "start:third", "stop:second"]
    assert [(entry["event"], entry["log_level"]) for entry in logs] == [
        ("component.shutdown_failed", "error"),
        ("component.shutdown_failed", "error"),
    ]


async def test_run_components_body_error_stops_all_and_keeps_body_error() -> None:
    """Тело упало, остановка одного тоже: остальные остановлены, наружу — ошибка тела, а не остановки."""
    events: list[str] = []
    body_error = ValueError("request failed")
    components = [
        FakeComponent(name="first", events=events),
        FakeComponent(name="second", events=events, shutdown_error=RuntimeError("stop failed")),
    ]

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 — проверяется identity, а не сообщение
        async with run_components(components=components, registry=ComponentRegistry()):
            raise body_error

    assert exc_info.value is body_error
    assert events == ["start:first", "start:second", "stop:first"]
