"""
Фикстуры infra-слоя auth: фейк email-транспорта и ``JobContext`` для тестов procrastinate-тасок.

``job_context`` собирает реальный ``JobContext`` с реестром компонентов в ``additional_context``,
а в реестре — фейк-транспорт: ровно так, как его наполняет worker на старте. ``App`` строится
поверх ``InMemoryConnector`` (без сети), ``Job`` — минимально валидный: таска читает только
``additional_context``, остальные поля контекста ей не нужны.
"""

import pytest
from procrastinate import App, JobContext
from procrastinate.testing import InMemoryConnector

from app.auth.application.ports.tasks import SEND_VERIFICATION_EMAIL_TASK
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email import EmailTransportPort
from app.shared.infra.procrastinate.component import WORKER_REGISTRY_KEY
from tests.builders import make_job
from tests.fakes import FakeEmailTransport


@pytest.fixture
def fake_email_transport() -> FakeEmailTransport:
    return FakeEmailTransport()


@pytest.fixture
def job_context(fake_email_transport: FakeEmailTransport) -> JobContext:
    registry = ComponentRegistry()
    registry.set(key=EmailTransportPort, value=fake_email_transport)
    app = App(connector=InMemoryConnector())
    return JobContext(
        app=app,
        job=make_job(task_name=SEND_VERIFICATION_EMAIL_TASK),
        start_timestamp=0.0,
        abort_reason=lambda: None,
        additional_context={WORKER_REGISTRY_KEY: registry},
    )
