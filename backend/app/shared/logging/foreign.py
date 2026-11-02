"""Правка записей чужих библиотек перед JSON-строкой: убрать шум и секреты."""

from structlog.typing import EventDict, WrappedLogger

from app.shared.types import DictStrAny

_TASK_ARGUMENT_KEYS = frozenset({"task_kwargs", "call_string"})


def hide_task_arguments(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """
    Убирает аргументы фоновых задач из записей procrastinate.

    procrastinate пишет аргументы задачи и в текст строки, и в поля ``job``/``jobs``, а среди аргументов бывают
    секреты — одноразовый код подтверждения email. Текст заменяется именем действия из поля ``action``: оно есть у
    каждой записи, в текст которой попадают аргументы.

    Scenarios:
        - постановка фоновой задачи из API
        - выполнение фоновой задачи воркером

    Args:
        _logger: Логгер (не используется; сигнатура процессора structlog)
        _method_name: Имя метода лога (не используется)
        event_dict: Поля строки

    Returns:
        Поля строки без аргументов задач; для записей других библиотек — без изменений
    """
    if not str(event_dict.get("logger", "")).startswith("procrastinate"):
        return event_dict

    replaced: DictStrAny = {}
    if isinstance(job := event_dict.get("job"), dict):
        replaced["job"] = _without_task_arguments(job)

    if isinstance(jobs := event_dict.get("jobs"), list):
        replaced["jobs"] = tuple(_without_task_arguments(job) for job in jobs if isinstance(job, dict))

    if action := event_dict.get("action"):
        replaced["event"] = f"procrastinate.{action}"

    return {**event_dict, **replaced}


def drop_color_message(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """
    Убирает поле ``color_message``: uvicorn кладёт туда текст строки с цветовыми escape-кодами терминала.

    Scenarios:
        - запись uvicorn в JSON-логе

    Args:
        _logger: Логгер (не используется; сигнатура процессора structlog)
        _method_name: Имя метода лога (не используется)
        event_dict: Поля строки

    Returns:
        Поля строки без ``color_message``
    """
    return {key: value for key, value in event_dict.items() if key != "color_message"}


def _without_task_arguments(job: DictStrAny) -> DictStrAny:
    """
    Копия описания задачи без её аргументов.

    Scenarios:
        - запись procrastinate о задаче

    Args:
        job: Описание задачи из записи procrastinate

    Returns:
        То же описание без ``task_kwargs`` и ``call_string``
    """
    return {key: value for key, value in job.items() if key not in _TASK_ARGUMENT_KEYS}
