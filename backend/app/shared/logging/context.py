"""Контекст строки лога: номер HTTP-запроса, в котором она написана, и значения, привязанные к этому запросу."""

import structlog
from opentelemetry import trace
from structlog.typing import EventDict, WrappedLogger


def bind_log_context(**values: object) -> None:
    """
    Привязывает значения к текущему запросу: structlog допишет их в каждую следующую строку лога этого запроса.

    Scenarios:
        - аутентификация запроса: ``user_id`` в строках лога запроса

    Args:
        **values: Поля строки лога и их значения
    """
    structlog.contextvars.bind_contextvars(**values)


def add_trace_context(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """
    Дописывает в строку лога номер запроса (``trace_id``) и текущего span'а (``span_id``), если строка
    пишется во время HTTP-запроса.

    По ``trace_id`` в Grafana находятся все строки одного запроса; ``span_id`` связывает строку со span'ом в
    трейсе. Вне запроса (старт, воркер, CLI) номеров нет, и строка не меняется.

    Scenarios:
        - любая строка лога, написанная во время HTTP-запроса API

    Args:
        _logger: Логгер (не используется; сигнатура процессора structlog)
        _method_name: Имя метода лога (не используется)
        event_dict: Поля строки

    Returns:
        Поля строки, с ``trace_id`` и ``span_id`` — если строка пишется внутри запроса
    """
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return event_dict

    return {
        **event_dict,
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }
