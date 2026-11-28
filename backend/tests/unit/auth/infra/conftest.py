import pytest
from procrastinate import JobContext

from app.auth.application.ports.tasks import SEND_VERIFICATION_EMAIL_TASK
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email import EmailTransportPort
from tests.builders import make_job, make_job_context
from tests.fakes import FakeEmailTransport


@pytest.fixture
def fake_email_transport() -> FakeEmailTransport:
    return FakeEmailTransport()


@pytest.fixture
def job_context(fake_email_transport: FakeEmailTransport) -> JobContext:
    registry = ComponentRegistry()
    registry.set(key=EmailTransportPort, value=fake_email_transport)
    return make_job_context(registry=registry, job=make_job(task_name=SEND_VERIFICATION_EMAIL_TASK))
