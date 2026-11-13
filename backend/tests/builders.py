"""
Тест-дата билдеры для доменных entity и value object'ов.

Обычные функции с kwargs-дефолтами и именованными аргументами; явные timestamp'ы
вместо заморозки времени (см. ``.claude/rules/python/testing.md``). Дефолты дают
«валидную» сущность; тест переопределяет только то, что проверяет.
"""

import datetime as dt
import hashlib
from uuid import UUID, uuid4

from procrastinate.jobs import Job

from app.auth.domain.entities import ChallengeEntity, RefreshTokenEntity, UserCredentialsEntity
from app.auth.domain.enums import ChallengeTypeEnum, UserPlanEnum, UserRoleEnum
from app.auth.domain.value_objects import Password
from app.geo.domain.entities import CityEntity
from app.geo.domain.value_objects import LocalizedNames
from app.geo.infra.datasets.manifest import DatasetFormatEnum, DatasetSpec
from app.journeys.application.ports.cities_client import CityLocationResponse
from app.journeys.domain.entities import JourneyEntity
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.domain.value_objects import GeoPoint
from app.shared.types import DictStrAny
from app.users.domain.entities import UserEntity

# Опорные координаты для детерминированных journeys/geo тестов (Москва→Лондон ≈ 2500 км).
_MOSCOW_LAT, _MOSCOW_LNG = 55.75, 37.62
_LONDON_LAT, _LONDON_LNG = 51.5, -0.12
MOSCOW_CITY_ID = UUID("00000000-0000-0000-0000-000000000001")
LONDON_CITY_ID = UUID("00000000-0000-0000-0000-000000000002")


def make_password(*, hash: str = "argon2-hash") -> Password:
    return Password(hash=hash)


def make_user_entity(
    *,
    user_id: UUID | None = None,
    display_name: str = "user",
    terms_accepted_at: dt.datetime | None = None,
    marketing_emails_consent: bool = False,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
    deleted_at: dt.datetime | None = None,
) -> UserEntity:
    return UserEntity(
        user_id=user_id or uuid4(),
        display_name=display_name,
        terms_accepted_at=terms_accepted_at or dt.datetime.now(tz=dt.UTC),
        marketing_emails_consent=marketing_emails_consent,
        created_at=created_at,
        updated_at=updated_at,
        deleted_at=deleted_at,
    )


def make_refresh_token(
    *,
    token_id: UUID | None = None,
    user_id: UUID | None = None,
    token_hash: str = "token-hash",
    expires_at: dt.datetime | None = None,
    revoked_at: dt.datetime | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
) -> RefreshTokenEntity:
    return RefreshTokenEntity(
        token_id=token_id or uuid4(),
        user_id=user_id or uuid4(),
        token_hash=token_hash,
        expires_at=expires_at or (dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=30)),
        revoked_at=revoked_at,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=created_at,
        updated_at=updated_at,
    )


def make_user_credentials(
    *,
    user_id: UUID | None = None,
    email: str = "user@example.com",
    username: str = "user",
    password: Password | None = None,
    role: UserRoleEnum = UserRoleEnum.USER,
    plan: UserPlanEnum = UserPlanEnum.FREE,
    email_verified_at: dt.datetime | None = None,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
) -> UserCredentialsEntity:
    return UserCredentialsEntity(
        user_id=user_id or uuid4(),
        email=email,
        username=username,
        password=password or make_password(),
        role=role,
        plan=plan,
        email_verified_at=email_verified_at,
        created_at=created_at,
        updated_at=updated_at,
    )


def make_challenge(
    *,
    challenge_id: UUID | None = None,
    user_id: UUID | None = None,
    challenge_type: ChallengeTypeEnum = ChallengeTypeEnum.EMAIL_VERIFICATION,
    code_ciphertext: str = "code-ciphertext",
    expires_at: dt.datetime | None = None,
    last_sent_at: dt.datetime | None = None,
    attempts: int = 0,
    used_at: dt.datetime | None = None,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
) -> ChallengeEntity:
    return ChallengeEntity(
        challenge_id=challenge_id or uuid4(),
        user_id=user_id or uuid4(),
        challenge_type=challenge_type,
        code_ciphertext=code_ciphertext,
        expires_at=expires_at or (dt.datetime.now(tz=dt.UTC) + dt.timedelta(minutes=15)),
        last_sent_at=last_sent_at or dt.datetime.now(tz=dt.UTC),
        attempts=attempts,
        used_at=used_at,
        created_at=created_at,
        updated_at=updated_at,
    )


def make_geo_point(
    *,
    city_id: UUID = MOSCOW_CITY_ID,
    country_code: str = "RU",
    latitude: float = _MOSCOW_LAT,
    longitude: float = _MOSCOW_LNG,
) -> GeoPoint:
    return GeoPoint(city_id=city_id, country_code=country_code, latitude=latitude, longitude=longitude)


def make_city_location_response(
    *,
    city_id: UUID = MOSCOW_CITY_ID,
    country_code: str = "RU",
    latitude: float = _MOSCOW_LAT,
    longitude: float = _MOSCOW_LNG,
) -> CityLocationResponse:
    return CityLocationResponse(city_id=city_id, country_code=country_code, latitude=latitude, longitude=longitude)


def make_journey(
    *,
    journey_id: UUID | None = None,
    user_id: UUID | None = None,
    origin: GeoPoint | None = None,
    destination: GeoPoint | None = None,
    transport_type: TransportTypeEnum = TransportTypeEnum.AIR,
    distance_km: int = 2500,
    traveled_year: int = 2020,
    sort_key: str | None = None,
    created_at: dt.datetime | None = None,
    updated_at: dt.datetime | None = None,
    deleted_at: dt.datetime | None = None,
) -> JourneyEntity:
    return JourneyEntity(
        journey_id=journey_id or uuid4(),
        user_id=user_id or uuid4(),
        origin=origin or make_geo_point(country_code="RU"),
        destination=destination
        or make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=_LONDON_LAT, longitude=_LONDON_LNG),
        transport_type=transport_type,
        distance_km=distance_km,
        traveled_year=traveled_year,
        sort_key=sort_key if sort_key is not None else f"{uuid4().hex}1",
        created_at=created_at,
        updated_at=updated_at,
        deleted_at=deleted_at,
    )


def make_city(
    *,
    city_id: UUID | None = None,
    en: str = "Moscow",
    ru: str | None = "Москва",
    country_code: str = "RU",
    latitude: float = _MOSCOW_LAT,
    longitude: float = _MOSCOW_LNG,
    population: int | None = 10_000_000,
) -> CityEntity:
    return CityEntity(
        city_id=city_id or uuid4(),
        names=LocalizedNames(en=en, ru=ru),
        country_code=country_code,
        latitude=latitude,
        longitude=longitude,
        population=population,
    )


def make_dataset_spec(
    *,
    content: bytes,
    name: str = "test-cities",
    format: DatasetFormatEnum = DatasetFormatEnum.CITIES,
    version: str = "2026-01-01",
    url: str = "https://example.test/test-cities.csv.gz",
) -> DatasetSpec:
    """Датасет манифеста, чей sha256 совпадает с ``content`` — байтами «скачиваемого» файла."""
    return DatasetSpec(
        name=name,
        format=format,
        version=version,
        url=url,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def make_job(
    *,
    job_id: int | None = None,
    task_name: str = "some_task",
    lock: str | None = None,
    task_kwargs: DictStrAny | None = None,
) -> Job:
    return Job(
        id=job_id,
        queue="default",
        lock=lock,
        queueing_lock=None,
        task_name=task_name,
        task_kwargs=task_kwargs or {},
    )
