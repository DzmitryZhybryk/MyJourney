"""
Фикстуры logging-тестов.

``restore_logging`` снимает и восстанавливает глобальное состояние логирования: root-logger, логгеры uvicorn,
structlog-дефолты и контекст лога. ``configure_logging`` и ``bind_log_context`` меняют его на весь процесс — без
restore это протекло бы в другие тесты. ``verification_job`` — задача письма с одноразовым кодом в аргументах.
``json_log_lines`` читает из перехваченного stdout строки, которые написал настоящий обработчик.
"""

import json
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
import structlog
from procrastinate.jobs import Job

from app.shared.types import DictStrAny

_UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")


@dataclass(frozen=True, slots=True)
class _LoggerState:
    level: int
    propagate: bool
    disabled: bool
    handlers: tuple[logging.Handler, ...]
    filters: tuple[Any, ...]


def _snapshot(logger: logging.Logger) -> _LoggerState:
    return _LoggerState(
        level=logger.level,
        propagate=logger.propagate,
        disabled=logger.disabled,
        handlers=tuple(logger.handlers),
        filters=tuple(logger.filters),
    )


def _restore(*, logger: logging.Logger, state: _LoggerState) -> None:
    logger.setLevel(state.level)
    logger.propagate = state.propagate
    logger.disabled = state.disabled
    logger.handlers[:] = state.handlers
    logger.filters[:] = state.filters


@pytest.fixture
def restore_logging() -> Iterator[None]:
    """Снимок root-logger'а и логгеров uvicorn с восстановлением после теста; structlog и контекст лога — в дефолт."""
    loggers = [logging.getLogger(), *(logging.getLogger(name) for name in _UVICORN_LOGGER_NAMES)]
    states = [_snapshot(logger) for logger in loggers]
    structlog.contextvars.clear_contextvars()
    yield
    for logger, state in zip(loggers, states, strict=True):
        _restore(logger=logger, state=state)

    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def json_log_lines(capsys: pytest.CaptureFixture[str]) -> Callable[[], tuple[DictStrAny, ...]]:
    """Читает строки, накопленные в stdout с прошлого чтения, и разбирает каждую как JSON."""

    def _read() -> tuple[DictStrAny, ...]:
        return tuple(json.loads(line) for line in capsys.readouterr().out.splitlines() if line)

    return _read


@pytest.fixture
def verification_job() -> Job:
    """Задача письма подтверждения: в аргументах email и одноразовый код, как их передаёт сервис."""
    return Job(
        id=42,
        queue="default",
        lock="email_verification:user:user-1",
        queueing_lock=None,
        task_name="send_verification_email",
        task_kwargs={"user_id": "user-1", "email": "ann@example.org", "code": "483921"},
    )
