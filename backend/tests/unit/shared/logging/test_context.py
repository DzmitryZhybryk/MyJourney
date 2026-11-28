"""
Unit-тесты контекста строки лога: номер HTTP-запроса из текущего span'а и значения, привязанные к запросу.

Span создаётся провайдером процесса (``get_tracer_provider``) — тем же, что даёт номера запросам API.
"""

import structlog
from structlog.testing import capture_logs

from app.shared.infra.telemetry import get_tracer_provider
from app.shared.logging.context import add_trace_context, bind_log_context


def test_add_trace_context_inside_span_adds_trace_and_span_ids() -> None:
    """Внутри span'а строка получает его trace_id (32 hex) и span_id (16 hex); остальные поля не меняются."""
    tracer = get_tracer_provider().get_tracer("test")
    with tracer.start_as_current_span("request") as span:
        event_dict = add_trace_context(None, "info", {"event": "test.event"})

    span_context = span.get_span_context()
    assert event_dict == {
        "event": "test.event",
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }


def test_add_trace_context_outside_span_leaves_line_unchanged() -> None:
    """Вне span'а (старт, воркер, CLI) строка остаётся как есть."""
    assert add_trace_context(None, "info", {"event": "test.event"}) == {"event": "test.event"}


def test_bind_log_context_adds_values_to_every_following_line(restore_logging: None) -> None:
    """Привязанное значение попадает в каждую следующую строку лога."""
    bind_log_context(user_id="user-1")

    with capture_logs(processors=[structlog.contextvars.merge_contextvars]) as logs:
        structlog.get_logger("test").info("test.first")
        structlog.get_logger("test").info("test.second")

    assert [entry["user_id"] for entry in logs] == ["user-1", "user-1"]
