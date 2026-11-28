"""
Unit-тесты ``ProcrastinateTaskBus`` поверх реального ``App`` + ``InMemoryConnector``.

Реальная App + in-memory коннектор (без сети, как в ``test_tasks.py``) — classicist:
ассертим итоговое состояние (job лёг в коннектор), а не порядок вызовов. Атомарный
defer в SA-транзакции (``ProcrastinateSessionBoundTaskBus.defer``) требует живой
сессии и проверяется на integration-уровне.
"""

from procrastinate.testing import InMemoryConnector
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.procrastinate.bus import ProcrastinateSessionBoundTaskBus, ProcrastinateTaskBus
from app.shared.infra.procrastinate.component import ProcrastinateApp


async def test_defer_enqueues_job_with_name_lock_and_args() -> None:
    """``defer`` ставит job в очередь с именем задачи, lock'ом и переданными kwargs."""
    connector = InMemoryConnector()
    app = ProcrastinateApp(connector=connector)

    @app.task(name="send_email")
    async def _send_email(to: str) -> None: ...

    async with app.open_async():
        await ProcrastinateTaskBus(app).defer(task_name="send_email", lock="user-1", to="user@example.com")

    jobs = connector.jobs
    assert len(jobs) == 1
    assert jobs[1]["task_name"] == "send_email"
    assert jobs[1]["lock"] == "user-1"
    assert jobs[1]["args"] == {"to": "user@example.com"}


def test_bind_to_returns_session_bound_bus() -> None:
    """``bind_to`` возвращает сессионно-привязанный view (``ProcrastinateSessionBoundTaskBus``)."""
    app = ProcrastinateApp(connector=InMemoryConnector())

    bound = ProcrastinateTaskBus(app).bind_to(AsyncSession())

    assert isinstance(bound, ProcrastinateSessionBoundTaskBus)
