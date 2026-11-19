"""
Переиспользуемые in-memory фейки, модуль на владельца порта: домен (``auth``, ``geo``,
``journeys``, ``media``, ``users``) или shared-вертикаль (``crypto``, ``di``, ``email``, ``procrastinate``).
"""

from tests.fakes.auth import (
    FakeAuthUnitOfWork,
    FakeChallengeRepository,
    FakeEmailVerificationService,
    FakeRefreshTokenRepository,
    FakeUserCredentialsRepository,
    FakeUsersClient,
)
from tests.fakes.crypto import FakeSaltedHasher
from tests.fakes.di import FakeComponent
from tests.fakes.email import FakeEmailTransport
from tests.fakes.geo import FakeCityRepository, FakeGeoUnitOfWork
from tests.fakes.journeys import FakeCitiesClient, FakeJourneyRepository, FakeJourneyUnitOfWork, MovementConnectionQuery
from tests.fakes.media import FakeS3ResponseStream
from tests.fakes.procrastinate import DeferredTask, FakeSessionBoundTaskBus, FakeTaskBus
from tests.fakes.users import FakeUserRepository, FakeUserUnitOfWork

__all__ = [
    "DeferredTask",
    "FakeAuthUnitOfWork",
    "FakeChallengeRepository",
    "FakeCitiesClient",
    "FakeCityRepository",
    "FakeComponent",
    "FakeEmailTransport",
    "FakeEmailVerificationService",
    "FakeGeoUnitOfWork",
    "FakeJourneyRepository",
    "FakeJourneyUnitOfWork",
    "FakeRefreshTokenRepository",
    "FakeS3ResponseStream",
    "FakeSaltedHasher",
    "FakeSessionBoundTaskBus",
    "FakeTaskBus",
    "FakeUserCredentialsRepository",
    "FakeUserRepository",
    "FakeUserUnitOfWork",
    "FakeUsersClient",
    "MovementConnectionQuery",
]
