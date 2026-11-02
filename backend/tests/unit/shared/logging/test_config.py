"""
Unit-тесты ``configure_logging`` на настоящей цепочке: запись логгера → JSON-строка в stdout.

Строки снимаются через ``capsys``: обработчик создаётся внутри теста и пишет в подменённый stdout. После настройки
пишем только через логгер, созданный в тесте, — логгеры модулей structlog кэширует. Порядок запуска API — сначала
uvicorn настраивает свои логгеры, потом приложение свои — воспроизводится его же ``LOGGING_CONFIG``. Глобальное
состояние восстанавливает ``restore_logging``.
"""

import copy
import json
import logging
import logging.config
from collections.abc import Callable

import pytest
import structlog
from procrastinate.jobs import Job
from uvicorn.config import LOGGING_CONFIG

from app.shared.infra.telemetry.tracing import get_tracer_provider
from app.shared.logging import bind_log_context, configure_logging
from app.shared.types import DictStrAny

type JsonLogLines = Callable[[], tuple[DictStrAny, ...]]


def test_configure_logging_sets_info_level_and_single_handler(restore_logging: None) -> None:
    """По умолчанию root-logger на INFO с единственным handler'ом."""
    configure_logging()

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1


def test_configure_logging_debug_enables_debug_level(restore_logging: None) -> None:
    """``include_debug=True`` поднимает root-logger на DEBUG."""
    configure_logging(include_debug=True)

    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_writes_json_line_with_request_context(
    restore_logging: None,
    json_log_lines: JsonLogLines,
) -> None:
    """Строка внутри запроса: свои поля плюс trace_id/span_id span'а, привязанный user_id, уровень, логгер, время."""
    configure_logging()
    bind_log_context(user_id="user-1")

    with get_tracer_provider().get_tracer("test").start_as_current_span("request") as span:
        structlog.get_logger("test.chain").info("test.event", answer=42)

    span_context = span.get_span_context()
    (line,) = json_log_lines()
    assert line["event"] == "test.event"
    assert line["answer"] == 42
    assert line["level"] == "info"
    assert line["logger"] == "test.chain"
    assert "timestamp" in line
    assert line["trace_id"] == format(span_context.trace_id, "032x")
    assert line["span_id"] == format(span_context.span_id, "016x")
    assert line["user_id"] == "user-1"


def test_configure_logging_routes_uvicorn_warnings_to_json_stdout(
    restore_logging: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ошибка uvicorn — JSON-строка в stdout, не текст в stderr; его INFO-строки не проходят."""
    logging.config.dictConfig(copy.deepcopy(LOGGING_CONFIG))
    configure_logging()

    logging.getLogger("uvicorn.error").info("Started server process")
    logging.getLogger("uvicorn.error").error("Application startup failed. Exiting.")

    captured = capsys.readouterr()
    assert captured.err == ""
    (line,) = (json.loads(text) for text in captured.out.splitlines())
    assert line["event"] == "Application startup failed. Exiting."
    assert line["level"] == "error"
    assert line["logger"] == "uvicorn.error"


def test_configure_logging_drops_uvicorn_duplicate_of_app_exception(
    restore_logging: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Строку uvicorn о необработанном исключении приложения отбрасываем: её уже написал middleware логирования."""
    logging.config.dictConfig(copy.deepcopy(LOGGING_CONFIG))
    configure_logging()

    try:
        raise RuntimeError("boom")  # noqa: TRY301 — исключение нужно ради exc_info в записи uvicorn
    except RuntimeError:
        logging.getLogger("uvicorn.error").error("Exception in ASGI application\n", exc_info=True)

    assert capsys.readouterr() == ("", "")


def test_configure_logging_silences_uvicorn_access_log(
    restore_logging: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Журнал запросов uvicorn молчит: строку на каждый запрос пишет middleware логирования."""
    logging.config.dictConfig(copy.deepcopy(LOGGING_CONFIG))
    configure_logging()

    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET", "/healthz/", "1.1", 200
    )

    assert capsys.readouterr() == ("", "")


def test_configure_logging_keeps_library_extras_without_color_message(
    restore_logging: None,
    json_log_lines: JsonLogLines,
) -> None:
    """Дополнительные поля записи чужой библиотеки попадают в JSON; цветная копия текста uvicorn — нет."""
    configure_logging()

    logging.getLogger("some.library").warning(
        "Something happened",
        extra={"action": "do_something", "details": {"attempt": 2}, "color_message": "\x1b[31mSomething\x1b[0m"},
    )

    (line,) = json_log_lines()
    assert line["action"] == "do_something"
    assert line["details"] == {"attempt": 2}
    assert "color_message" not in line


def test_configure_logging_hides_procrastinate_task_arguments(
    restore_logging: None,
    capsys: pytest.CaptureFixture[str],
    verification_job: Job,
) -> None:
    """Строка воркера о задаче проходит настоящую цепочку без кода и email; id задачи и действие остаются."""
    configure_logging()

    logging.getLogger("procrastinate.worker").info(
        f"Starting job {verification_job.call_string}",
        extra={"action": "start_job", "job": verification_job.log_context()},
    )

    output = capsys.readouterr().out
    assert str(verification_job.task_kwargs["code"]) not in output
    assert str(verification_job.task_kwargs["email"]) not in output
    (line,) = (json.loads(text) for text in output.splitlines())
    assert line["event"] == "procrastinate.start_job"
    assert line["job"]["id"] == verification_job.id
