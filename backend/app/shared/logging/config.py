import logging
import sys

import structlog
from structlog.typing import Processor

from app.shared.logging.context import add_trace_context
from app.shared.logging.foreign import drop_color_message, hide_task_arguments
from app.shared.utils.json_serializer import serialize_to_json

_UVICORN_APP_EXCEPTION_PREFIX = "Exception in ASGI application"


def configure_logging(include_debug: bool = False) -> None:
    """
    Настраивает логирование процесса: каждая запись — одна JSON-строка в stdout, от structlog и от стандартного
    ``logging`` одинаково.

    Scenarios:
        - запуск API, воркера и CLI-скриптов

    Args:
        include_debug: Писать ли записи уровня DEBUG
    """
    shared_processors = get_shared_processors()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        fmt=structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[
                *shared_processors,
                structlog.stdlib.ExtraAdder(),
                drop_color_message,
                hide_task_arguments,
            ],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(serializer=serialize_to_json),
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(hdlr=handler)
    root_logger.setLevel(logging.DEBUG if include_debug else logging.INFO)

    _route_uvicorn_logs_to_root()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
        context_class=dict,
    )


def get_shared_processors() -> tuple[Processor, ...]:
    """
    Возвращает процессоры, через которые проходит каждая строка лога — наша и чужих библиотек.

    Scenarios:
        - настройка логирования процесса
        - тесты строк лога, которым нужна настоящая цепочка процессоров

    Returns:
        Процессоры в порядке применения
    """
    return (
        structlog.contextvars.merge_contextvars,
        add_trace_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Получает настроенный логгер structlog.

    Scenarios:
        - любой модуль, который пишет в лог

    Args:
        name: Имя логгера (обычно __name__ модуля). Если None, используется имя вызывающего модуля.

    Returns:
        Настроенный BoundLogger с поддержкой структурированного логирования.

    Example:
        logger = get_logger(__name__)
        logger.info("journey.created", journey_id=journey_id)
    """
    return structlog.get_logger(name)


def _route_uvicorn_logs_to_root() -> None:
    """
    Пускает логи uvicorn через наш JSON-обработчик, чтобы ошибки сервера и падение старта попадали в лог.

    Свой текстовый обработчик uvicorn вешает на родительский логгер ``uvicorn`` — его и снимаем. Строку о
    необработанном исключении отбрасываем: такую же с трейсбеком уже написал middleware логирования. Журнал
    запросов uvicorn выключен — строку на каждый запрос пишет то же middleware.

    Scenarios:
        - запуск API под uvicorn
    """
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(logging.WARNING)
    uvicorn_error_logger.addFilter(_is_not_app_exception_duplicate)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False


def _is_not_app_exception_duplicate(record: logging.LogRecord) -> bool:
    """
    Отличает запись uvicorn о необработанном исключении приложения от остальных его записей.

    Scenarios:
        - необработанное исключение в HTTP-запросе: в лог попадает одна строка, от middleware логирования

    Args:
        record: Запись логгера ``uvicorn.error``

    Returns:
        ``False`` для записи о необработанном исключении, иначе ``True``
    """
    return not str(record.msg).startswith(_UVICORN_APP_EXCEPTION_PREFIX)
