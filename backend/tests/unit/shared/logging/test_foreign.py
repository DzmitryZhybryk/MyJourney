"""
Unit-тесты правки записей чужих библиотек: аргументы фоновых задач procrastinate и цветной текст uvicorn.

Записи собраны так, как их пишет сама библиотека: описание задачи — ``Job.log_context()``, текст воркера — с
``call_string``.
"""

import pytest
from procrastinate.jobs import Job

from app.shared.logging.foreign import drop_color_message, hide_task_arguments


def test_hide_task_arguments_in_worker_line(verification_job: Job) -> None:
    """Строка воркера о задаче: аргументов нет ни в тексте, ни в ``job``; событие — действие; id и имя остаются."""
    event_dict = {
        "event": f"Starting job {verification_job.call_string}",
        "logger": "procrastinate.worker",
        "action": "start_job",
        "job": verification_job.log_context(),
    }

    hidden = hide_task_arguments(None, "info", event_dict)

    assert hidden["event"] == "procrastinate.start_job"
    assert hidden["job"]["id"] == verification_job.id
    assert hidden["job"]["task_name"] == "send_verification_email"
    assert str(verification_job.task_kwargs["code"]) not in str(hidden)
    assert str(verification_job.task_kwargs["email"]) not in str(hidden)


def test_hide_task_arguments_in_deferral_line(verification_job: Job) -> None:
    """Строка постановки задачи из API: аргументов нет ни в одном описании ``jobs``; событие — действие."""
    event_dict = {
        "event": "Deferred 1 job",
        "logger": "procrastinate.jobs",
        "action": "jobs_deferred",
        "jobs": [verification_job.log_context()],
    }

    hidden = hide_task_arguments(None, "info", event_dict)

    assert hidden["event"] == "procrastinate.jobs_deferred"
    assert [job["id"] for job in hidden["jobs"]] == [verification_job.id]
    assert str(verification_job.task_kwargs["code"]) not in str(hidden)
    assert str(verification_job.task_kwargs["email"]) not in str(hidden)


@pytest.mark.parametrize(
    "event_dict",
    [
        {"event": "some.event", "logger": "other.library", "action": "start_job", "job": {"task_kwargs": {"a": 1}}},
        {"event": "Adding tasks from blueprint", "logger": "procrastinate.blueprints"},
    ],
)
def test_hide_task_arguments_leaves_lines_without_task_arguments_unchanged(event_dict: dict[str, object]) -> None:
    """Записи других библиотек и записи procrastinate без действия и задачи не меняются."""
    assert hide_task_arguments(None, "info", event_dict) == event_dict


def test_drop_color_message_removes_only_color_message() -> None:
    """Цветная копия текста от uvicorn убирается, остальные поля остаются."""
    event_dict = {
        "event": "Invalid HTTP request received.",
        "color_message": "\x1b[31mInvalid\x1b[0m",
        "level": "warning",
    }

    assert drop_color_message(None, "warning", event_dict) == {
        "event": "Invalid HTTP request received.",
        "level": "warning",
    }
