"""Атомарная постановка в транзакции сессии требует живой базы и проверяется на integration-уровне."""

from procrastinate.testing import InMemoryConnector
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.procrastinate.bus import ProcrastinateSessionBoundTaskBus, ProcrastinateTaskBus
from app.shared.infra.procrastinate.component import ProcrastinateApp


async def test_defer_enqueues_job_with_name_lock_and_args() -> None:
    """Задача встаёт в очередь с именем, lock'ом и переданными аргументами."""
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
    """Привязка к сессии отдаёт ``ProcrastinateSessionBoundTaskBus``."""
    app = ProcrastinateApp(connector=InMemoryConnector())

    bound = ProcrastinateTaskBus(app).bind_to(AsyncSession())

    assert isinstance(bound, ProcrastinateSessionBoundTaskBus)
