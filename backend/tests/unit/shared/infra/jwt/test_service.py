import datetime as dt
from uuid import uuid4

import jwt
import pytest

from app.shared.infra.jwt import AccessTokenClaims, JWTDecodeError
from app.shared.infra.jwt.service import JWTService
from app.shared.types import DictStrAny

_ISSUED_AT = int(dt.datetime(2026, 1, 1, tzinfo=dt.UTC).timestamp())
_FAR_FUTURE = int(dt.datetime(2100, 1, 1, tzinfo=dt.UTC).timestamp())
_VALID_CLAIMS: DictStrAny = {
    "role": "user",
    "plan": "free",
    "email_verified": True,
    "iat": _ISSUED_AT,
    "exp": _FAR_FUTURE,
}


def test_decode_access_token_roundtrips_claims(jwt_service: JWTService) -> None:
    """Токен, выпущенный сервисом, декодируется обратно в те же claims, права — тем же набором."""
    claims = AccessTokenClaims(
        user_id=uuid4(),
        role="admin",
        plan="premium",
        permissions=frozenset({"b.permission", "a.permission"}),
        email_verified=True,
    )

    token = jwt_service.create_access_token(claims=claims)

    assert jwt_service.decode_access_token(token) == claims


def test_decode_access_token_without_permissions_claim_has_no_permissions(
    jwt_service: JWTService,
    jwt_secret: str,
    jwt_algorithm: str,
) -> None:
    """Токен без claim'а permissions (выпущен до появления прав) → пустой набор прав, а не ошибка."""
    token = jwt.encode({"sub": str(uuid4()), **_VALID_CLAIMS}, jwt_secret, algorithm=jwt_algorithm)

    assert jwt_service.decode_access_token(token).permissions == frozenset()


@pytest.mark.parametrize("permissions", ["media.config.edit", ["media.config.edit", 1], {"a": 1}, None])
def test_decode_access_token_malformed_permissions_raises(
    jwt_service: JWTService,
    jwt_secret: str,
    jwt_algorithm: str,
    permissions: object,
) -> None:
    """Claim permissions есть, но это не список строк — ошибка выпуска → JWTDecodeError, а не тихий 403."""
    token = jwt.encode(
        {"sub": str(uuid4()), **_VALID_CLAIMS, "permissions": permissions},
        jwt_secret,
        algorithm=jwt_algorithm,
    )

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


@pytest.mark.parametrize(
    "broken_claims",
    [
        {"role": None},
        {"plan": None},
        {"email_verified": None},
        {"role": 1},
        {"plan": 1},
        {"email_verified": "true"},
        {"iat": None},
        {"exp": None},
    ],
)
def test_decode_access_token_missing_or_mistyped_claim_raises(
    jwt_service: JWTService,
    jwt_secret: str,
    jwt_algorithm: str,
    broken_claims: DictStrAny,
) -> None:
    """role, plan, email_verified, iat или exp отсутствует или неверного типа → JWTDecodeError."""
    payload = {"sub": str(uuid4()), **_VALID_CLAIMS, **broken_claims}
    payload = {key: value for key, value in payload.items() if value is not None}
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_invalid_signature_raises(jwt_service: JWTService, jwt_algorithm: str) -> None:
    """Токен, подписанный чужим секретом, → JWTDecodeError (неверная подпись)."""
    token = jwt.encode({"sub": str(uuid4())}, "another-secret-at-least-32-bytes-long", algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_expired_raises(jwt_service: JWTService, jwt_secret: str, jwt_algorithm: str) -> None:
    """Истёкший токен (exp в прошлом) → JWTDecodeError."""
    expired_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=1)
    token = jwt.encode({"sub": str(uuid4()), "exp": expired_at}, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_malformed_raises(jwt_service: JWTService) -> None:
    """Строка, не являющаяся JWT, → JWTDecodeError."""
    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token("not-a-jwt")


def test_decode_access_token_missing_sub_raises(
    jwt_service: JWTService,
    jwt_secret: str,
    jwt_algorithm: str,
) -> None:
    """Валидная подпись, но claim sub отсутствует → JWTDecodeError."""
    token = jwt.encode(_VALID_CLAIMS, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)


def test_decode_access_token_non_uuid_sub_raises(jwt_service: JWTService, jwt_secret: str, jwt_algorithm: str) -> None:
    """Валидная подпись, sub-строка, но не UUID → JWTDecodeError."""
    token = jwt.encode({"sub": "not-a-uuid", **_VALID_CLAIMS}, jwt_secret, algorithm=jwt_algorithm)

    with pytest.raises(JWTDecodeError):
        jwt_service.decode_access_token(token)
