"""
Корневой conftest тест-suite.

Содержит две инфраструктурные вещи на весь suite:

1. **Bootstrap настроек** — цикл ``os.environ.setdefault`` ниже выполняется на
   импорте conftest, то есть **до** импорта любого ``app``-модуля. Почти любой
   импорт ``app`` тянет ``app.shared.settings.settings`` (синглтон строится на
   импорте, ``@cache`` + ``frozen``), которому нужны обязательные поля ``Settings``.
   Значения — мусорные заглушки, чтобы ``Settings()`` не падал на коллекции;
   unit-тесты читают конфиг из конструктора, а не из синглтона (см.
   ``.claude/rules/python/testing.md``). ``setdefault`` оставляет приоритет за
   реальным окружением/CI.
2. **Авто-маркировка** — хук ``pytest_collection_modifyitems`` проставляет маркеры
   по пути файла (подробности — в его докстринге).
"""

import os

import pytest

_TEST_ENV_DEFAULTS = {
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test",
    "HOST": "localhost",
    "PORT": "8000",
    "ENVIRONMENT": "local",
    "JWT_SECRET_KEY": "test-secret-key-at-least-32-bytes-long",
    "CHALLENGE_CODE_ENCRYPTION_KEY": "oh_PRYy2ap1CNNTxWoeJY-mNqAOYdnFYPEB7df0H63k=",
    "RESEND_API_KEY": "test-resend-key",
    "RESEND_FROM_EMAIL": "test@example.com",
    "MEDIA_S3_ENDPOINT_URL": "http://s3.localhost:9050",
    "MEDIA_S3_ACCESS_KEY_ID": "test-access-key",
    "MEDIA_S3_SECRET_ACCESS_KEY": "test-secret-key",
}

for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


# Импорты app/tests.fakes — строго ПОСЛЕ env-bootstrap: ``app`` на импорте строит
# синглтон ``settings``, которому нужны заполненные env-поля (E402 осознанно).
from app.auth.application.config import EmailVerificationConfig  # noqa: E402
from app.shared.infra.crypto import get_fernet_secret_cipher  # noqa: E402
from app.shared.infra.crypto.fernet import FernetSecretCipher  # noqa: E402
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher  # noqa: E402
from tests.builders import LONDON_CITY_ID, make_city_location_response  # noqa: E402
from tests.fakes import (  # noqa: E402
    FakeAuthUnitOfWork,
    FakeChallengeRepository,
    FakeCitiesClient,
    FakeCityRepository,
    FakeGeoUnitOfWork,
    FakeJourneyRepository,
    FakeJourneyUnitOfWork,
    FakeRefreshTokenRepository,
    FakeSaltedHasher,
    FakeTaskBus,
    FakeUserCredentialsRepository,
    FakeUserRepository,
    FakeUsersClient,
    FakeUserUnitOfWork,
)

_EMAIL_VERIFICATION_TTL_MINUTES = 15
_EMAIL_VERIFICATION_MAX_ATTEMPTS = 5
_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = 60


# Оси маркеров, выводимые из пути файла: tests/<level>/<domain>/...
# При добавлении нового уровня/домена обнови и эти кортежи, и список ``markers`` в
# pyproject.toml (``--strict-markers`` запрещает незарегистрированные маркеры).
_LEVEL_MARKERS = ("unit", "integration", "api")
_DOMAIN_MARKERS = ("auth", "users", "shared", "journeys", "geo", "health", "media")

# Потолок времени на один тест по уровню. Integration считает только сам тест: подъём
# контейнера в session-фикстуре приходится на setup первого теста и в лимит не входит.
_LEVEL_TIMEOUTS = {
    "unit": pytest.mark.timeout(timeout=1),
    "api": pytest.mark.timeout(timeout=1),
    "integration": pytest.mark.timeout(timeout=30, func_only=True),
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Автоматически проставляет тестам маркеры уровня и домена по пути файла.

    Каталог ``tests/<уровень>/<домен>/...`` уже кодирует две оси, по которым мы
    хотим запускать тесты выборочно: уровень (``unit``/``integration``/``api``) и
    домен (``auth``/``users``/``shared``). На этапе сбора хук смотрит ``nodeid``
    каждого теста и, если сегмент пути совпадает с известным маркером, навешивает
    его. Благодаря этому маркеры в самих тест-файлах ставить **не нужно** — и их
    нельзя забыть: разметка следует из расположения файла, а не из ручных
    декораторов (забытый ручной маркер молча выкинул бы тест из выборки).

    Маркеры pytest композируются булевой логикой, поэтому доступна выборка по любой
    комбинации осей:

    - ``pytest -m unit`` / ``make test-unit`` — все юнит-тесты (любой домен);
    - ``pytest -m users`` / ``make test-users`` — все тесты домена users (любой уровень);
    - ``uv run pytest -m "unit and users"`` — пересечение осей (отдельного make-таргета нет).

    Заодно по уровню ставит потолок времени на тест (``_LEVEL_TIMEOUTS``): тест, упёршийся в
    него, сначала разбирают; поднимают лимит понемногу и только по объективной причине.

    Args:
        items: Собранные pytest'ом тест-элементы; маркеры добавляются in-place.
    """
    known_markers = (*_LEVEL_MARKERS, *_DOMAIN_MARKERS)
    for item in items:
        path_segments = item.nodeid.split("/")
        for marker_name in known_markers:
            if marker_name in path_segments:
                item.add_marker(getattr(pytest.mark, marker_name))

        level = next((name for name in _LEVEL_MARKERS if name in path_segments), None)
        if level is not None:
            item.add_marker(_LEVEL_TIMEOUTS[level])


# Фикстуры, переиспользуемые между УРОВНЯМИ (unit + api). Каталоги нарезаны
# уровень→домен, поэтому единственный общий предок ``tests/unit/auth`` и
# ``tests/api/auth`` — этот корневой conftest; иначе фейки дублировались бы в обоих.
# Доменно-специфичную проводку сервисов (``auth_service`` и т.п.) держат per-domain conftest'ы.


@pytest.fixture
def fake_user_credentials_repository() -> FakeUserCredentialsRepository:
    return FakeUserCredentialsRepository()


@pytest.fixture
def fake_refresh_token_repository() -> FakeRefreshTokenRepository:
    return FakeRefreshTokenRepository()


@pytest.fixture
def fake_challenge_repository() -> FakeChallengeRepository:
    return FakeChallengeRepository()


@pytest.fixture
def fake_uow(
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> FakeAuthUnitOfWork:
    # Репозитории — отдельные фикстуры тех же инстансов: тест сидит/ассертит их состояние
    # по конкретному типу (на uow они под port-типом, без .by_user_id/.challenges).
    return FakeAuthUnitOfWork(
        user_credentials_repository=fake_user_credentials_repository,
        refresh_token_repository=fake_refresh_token_repository,
        challenge_repository=fake_challenge_repository,
    )


@pytest.fixture
def fake_users_client() -> FakeUsersClient:
    return FakeUsersClient()


@pytest.fixture
def fake_user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def fake_user_uow(fake_user_repository: FakeUserRepository) -> FakeUserUnitOfWork:
    # Репозиторий — отдельная фикстура того же инстанса: тест сидит/ассертит его состояние
    # по конкретному типу (на uow он под port-типом, без .by_user_id).
    return FakeUserUnitOfWork(user_repository=fake_user_repository)


@pytest.fixture
def fake_salted_hasher() -> FakeSaltedHasher:
    return FakeSaltedHasher()


@pytest.fixture
def secret_cipher() -> FernetSecretCipher:
    # Ключ из settings, а не литерал: в api-тестах код шифрует сам тест, а расшифровывает приложение.
    return get_fernet_secret_cipher()


@pytest.fixture
def fake_task_bus() -> FakeTaskBus:
    return FakeTaskBus()


@pytest.fixture
def deterministic_hasher() -> Sha256DeterministicHasher:
    """Реальный sha256-hasher для сидинга ``token_hash`` (тот же, что у боевого token_issuer)."""
    return Sha256DeterministicHasher()


@pytest.fixture
def fake_city_repository() -> FakeCityRepository:
    return FakeCityRepository()


@pytest.fixture
def fake_geo_uow(fake_city_repository: FakeCityRepository) -> FakeGeoUnitOfWork:
    return FakeGeoUnitOfWork(city_repository=fake_city_repository)


@pytest.fixture
def fake_cities_client() -> FakeCitiesClient:
    """Справочник с Москвой и Лондоном — в порядке запроса поездки Москва → Лондон."""
    return FakeCitiesClient(
        locations=(
            make_city_location_response(),
            make_city_location_response(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
        )
    )


@pytest.fixture
def fake_journey_repository() -> FakeJourneyRepository:
    return FakeJourneyRepository()


@pytest.fixture
def fake_journey_uow(fake_journey_repository: FakeJourneyRepository) -> FakeJourneyUnitOfWork:
    # Репозиторий — отдельная фикстура того же инстанса: тест сидит/ассертит его состояние
    # по конкретному типу (на uow он под port-типом, без .journeys).
    return FakeJourneyUnitOfWork(journey_repository=fake_journey_repository)


@pytest.fixture
def email_verification_config() -> EmailVerificationConfig:
    return EmailVerificationConfig(
        ttl_minutes=_EMAIL_VERIFICATION_TTL_MINUTES,
        max_attempts=_EMAIL_VERIFICATION_MAX_ATTEMPTS,
        resend_cooldown_seconds=_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    )
