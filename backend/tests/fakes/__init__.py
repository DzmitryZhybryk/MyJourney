"""
Переиспользуемые in-memory фейки, модуль на владельца порта: домен (``auth``, ``backoffice``, ``geo``,
``journeys``, ``media``, ``users``) или shared-вертикаль (``crypto``, ``di``, ``email``, ``events``, ``procrastinate``).
"""

from tests.fakes.auth import (
    FakeAuthUnitOfWork,
    FakeChallengeRepository,
    FakeEmailVerificationService,
    FakeRefreshTokenRepository,
    FakeUserCredentialsRepository,
    FakeUsersClient,
)
from tests.fakes.backoffice import AccountsPageQuery, FakeAccountRepository, FakeBackofficeUnitOfWork
from tests.fakes.crypto import FakeSaltedHasher
from tests.fakes.di import FakeComponent
from tests.fakes.email import FakeEmailTransport
from tests.fakes.events import FakeEventPublisher, FakeSessionBoundEventPublisher
from tests.fakes.geo import FakeCityRepository, FakeGeoUnitOfWork
from tests.fakes.journeys import FakeCitiesClient, FakeJourneyRepository, FakeJourneyUnitOfWork, MovementConnectionQuery
from tests.fakes.media import FakeMediaConfigRepository, FakeMediaUnitOfWork, FakeS3ResponseStream
from tests.fakes.procrastinate import DeferredTask, FakeSessionBoundTaskBus, FakeTaskBus
from tests.fakes.users import FakeUserRepository, FakeUserUnitOfWork

__all__ = [
    "AccountsPageQuery",
    "DeferredTask",
    "FakeAccountRepository",
    "FakeAuthUnitOfWork",
    "FakeBackofficeUnitOfWork",
    "FakeChallengeRepository",
    "FakeCitiesClient",
    "FakeCityRepository",
    "FakeComponent",
    "FakeEmailTransport",
    "FakeEmailVerificationService",
    "FakeEventPublisher",
    "FakeGeoUnitOfWork",
    "FakeJourneyRepository",
    "FakeJourneyUnitOfWork",
    "FakeMediaConfigRepository",
    "FakeMediaUnitOfWork",
    "FakeRefreshTokenRepository",
    "FakeS3ResponseStream",
    "FakeSaltedHasher",
    "FakeSessionBoundEventPublisher",
    "FakeSessionBoundTaskBus",
    "FakeTaskBus",
    "FakeUserCredentialsRepository",
    "FakeUserRepository",
    "FakeUserUnitOfWork",
    "FakeUsersClient",
    "MovementConnectionQuery",
]
